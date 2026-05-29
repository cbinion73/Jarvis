import SwiftUI
import EventKit
import CoreLocation
import JarvisKit

// MARK: - SettingsView  "Systems"

struct SettingsView: View {

    @ObservedObject private var eventSync = EventKitSyncManager.shared
    @ObservedObject private var healthSync = HealthSyncManager.shared
    @ObservedObject private var geofence = GeofenceManager.shared
    @ObservedObject private var weatherLocation = WeatherLocationProvider.shared

    @State private var serverOK = false
    @State private var watchStatus: WatchStatus?
    @State private var appState: AppStateOverview?
    @State private var pingError: String?
    @State private var isRefreshing = false

    private let steel = Color(red: 0.55, green: 0.65, blue: 0.78)

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 14) {

                        // ── Status banner ──────────────────────────
                        HStack(spacing: 14) {
                            ZStack {
                                Circle().fill(serverOK ? Color.green.opacity(0.15) : Color.red.opacity(0.1))
                                    .frame(width: 44, height: 44)
                                Image(systemName: serverOK ? "server.rack" : "exclamationmark.triangle.fill")
                                    .font(.system(size: 18))
                                    .foregroundStyle(serverOK ? .green : .red)
                            }
                            VStack(alignment: .leading, spacing: 2) {
                                Text(serverOK ? "SYSTEMS NOMINAL" : "CONNECTION ERROR")
                                    .font(.system(size: 10, weight: .black))
                                    .tracking(1.2)
                                    .foregroundStyle(serverOK ? .green : .red)
                                if let watchStatus {
                                    Text("\(watchStatus.mode.capitalized) · \(watchStatus.needsCount) needs · \(watchStatus.weather)")
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                        .lineLimit(1)
                                } else {
                                    Text(JARVISEnvironment.baseURL.host ?? "—")
                                        .font(.caption2.monospaced())
                                        .foregroundStyle(.secondary)
                                        .lineLimit(1)
                                }
                            }
                            Spacer()
                            // Ping button
                            Button {
                                Task { await refreshSystems() }
                            } label: {
                                if isRefreshing {
                                    ProgressView().tint(steel)
                                } else {
                                    Text("Refresh")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(steel)
                                }
                            }
                            .glassEffect(in: Capsule())
                        }
                        .padding(14)
                        .glassEffect(in: RoundedRectangle(cornerRadius: 16))

                        // ── Server environment ──────────────────────
                        SystemsSection(title: "Server", icon: "wifi", accent: steel) {
                            HStack {
                                Text("Environment")
                                    .font(.caption).foregroundStyle(.secondary)
                                Spacer()
                                Text("Production")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.green)
                            }

                            Text("This app is locked to the live JARVIS production server.")
                                .font(.caption)
                                .foregroundStyle(.secondary)

                            Divider().opacity(0.3)

                            HStack {
                                Text("Base URL")
                                    .font(.caption).foregroundStyle(.secondary)
                                Spacer()
                                Text(JARVISEnvironment.baseURL.absoluteString)
                                    .font(.caption.monospaced())
                                    .foregroundStyle(steel.opacity(0.9))
                                    .lineLimit(1)
                                    .truncationMode(.middle)
                            }

                            if let watchStatus {
                                Divider().opacity(0.3)

                                HStack(spacing: 10) {
                                    systemsMetric("Mode", watchStatus.mode.capitalized)
                                    systemsMetric("Needs", "\(watchStatus.needsCount)")
                                    systemsMetric("Drift", watchStatus.drift ? "Yes" : "No")
                                }
                            }

                            if let appState {
                                Divider().opacity(0.3)
                                HStack(spacing: 10) {
                                    systemsMetric("Notifications", "\(appState.notifications.pendingCount)")
                                    systemsMetric("Calendar", "\(appState.calendar.count)")
                                    systemsMetric("Reminders", "\(appState.reminders.count)")
                                }
                                if !appState.server.weather.isEmpty {
                                    SysRow(label: "Weather") {
                                        Text(appState.server.weather)
                                            .foregroundStyle(.white)
                                            .lineLimit(1)
                                    }
                                }
                                SysRow(label: "Server Timestamp") {
                                    Text(nonEmpty(appState.server.ts, fallback: nil))
                                        .foregroundStyle(.white)
                                }
                            }

                            if let pingError, !pingError.isEmpty {
                                Divider().opacity(0.3)
                                Text(pingError)
                                    .font(.caption)
                                    .foregroundStyle(.red.opacity(0.9))
                            }
                        }

                        // ── Sync health ─────────────────────────────
                        SystemsSection(title: "Sync", icon: "arrow.triangle.2.circlepath", accent: steel) {
                            SysRow(label: "Calendar") {
                                syncStatusChip(label: eventKitStatusLabel(eventSync.calendarStatus))
                            }
                            SysRow(label: "Reminders") {
                                syncStatusChip(label: eventKitStatusLabel(eventSync.remindersStatus))
                            }
                            SysRow(label: "Last Sync") {
                                Text(formatDate(eventSync.lastSyncDate))
                                    .foregroundStyle(.white)
                            }
                            SysRow(label: "Pushed") {
                                Text("\(eventSync.lastEventCount) events · \(eventSync.lastReminderCount) reminders")
                                    .foregroundStyle(.white)
                            }
                            if let appState {
                                SysRow(label: "Server Mirror") {
                                    Text("\(appState.calendar.count) events · \(appState.reminders.count) reminders")
                                        .foregroundStyle(.white)
                                }
                                SysRow(label: "Mirrored At") {
                                    Text(nonEmpty(appState.calendar.syncedAt, fallback: appState.reminders.syncedAt))
                                        .foregroundStyle(.white)
                                }
                                Divider().opacity(0.3)
                                syncHealthRow(label: "Calendar Mirror", domain: appState.syncHealth.calendar)
                                syncHealthRow(label: "Reminders Mirror", domain: appState.syncHealth.reminders)
                                syncHealthRow(label: "Focus Mirror", domain: appState.syncHealth.focus)
                                syncHealthRow(label: "Now Playing Mirror", domain: appState.syncHealth.nowPlaying)
                                syncHealthRow(label: "Sound Mirror", domain: appState.syncHealth.soundAlert)
                                syncHealthRow(label: "Vision Mirror", domain: appState.syncHealth.visionScan)
                            }

                            Button {
                                Task { await refreshEventSync() }
                            } label: {
                                Label(eventSync.isSyncing ? "Syncing…" : "Sync Calendar & Reminders", systemImage: "calendar.badge.clock")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(steel)
                        }

                        // ── Health mirror ───────────────────────────
                        SystemsSection(title: "Health", icon: "heart.text.square.fill", accent: .pink) {
                            SysRow(label: "Authorized") {
                                syncStatusChip(label: healthSync.isAuthorized ? "Connected" : "Not Connected")
                            }
                            SysRow(label: "Last Sync") {
                                Text(formatDate(healthSync.lastSyncDate))
                                    .foregroundStyle(.white)
                            }
                            SysRow(label: "Samples") {
                                Text("\(healthSync.lastSyncedCount)")
                                    .foregroundStyle(.white)
                            }
                            if let syncError = healthSync.syncError, !syncError.isEmpty {
                                Text(syncError)
                                    .font(.caption)
                                    .foregroundStyle(.red.opacity(0.9))
                            }

                            Button {
                                Task { await refreshHealthSync() }
                            } label: {
                                Label(healthSync.isSyncing ? "Syncing…" : "Sync HealthKit", systemImage: "waveform.path.ecg")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(.pink)
                        }

                        SystemsSection(title: "Attention", icon: "bell.badge.fill", accent: .yellow) {
                            SysRow(label: "Notifications") {
                                Text("\(appState?.notifications.pendingCount ?? 0)")
                                    .foregroundStyle(.white)
                            }
                            SysRow(label: "Focus") {
                                syncStatusChip(label: (appState?.focus.focusActive ?? false) ? "Active" : "Inactive")
                            }
                            SysRow(label: "Now Playing") {
                                Text(appState?.nowPlaying.title.isEmpty == false ? appState?.nowPlaying.title ?? "—" : "Nothing playing")
                                    .foregroundStyle(.white)
                                    .lineLimit(1)
                            }
                            if let soundLabel = appState?.soundAlert.label, !soundLabel.isEmpty {
                                SysRow(label: "Last Sound") {
                                    Text(soundLabel)
                                        .foregroundStyle(.white)
                                        .lineLimit(1)
                                }
                            }
                            if let scanPreview = appState?.visionScan.textPreview, !scanPreview.isEmpty {
                                Text(scanPreview)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(3)
                            }
                            if let recentNotifications = appState?.notifications.recent, !recentNotifications.isEmpty {
                                Divider().opacity(0.3)
                                VStack(alignment: .leading, spacing: 10) {
                                    ForEach(Array(recentNotifications.prefix(3))) { notification in
                                        VStack(alignment: .leading, spacing: 3) {
                                            HStack(alignment: .firstTextBaseline) {
                                                Text(notification.title.isEmpty ? "JARVIS Alert" : notification.title)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                Spacer()
                                                if !notification.category.isEmpty {
                                                    syncStatusChip(label: notification.category.capitalized)
                                                }
                                            }
                                            if !notification.body.isEmpty {
                                                Text(notification.body)
                                                    .font(.caption)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(3)
                                            }
                                            if let createdAt = notification.createdAt, !createdAt.isEmpty {
                                                Text(nonEmpty(createdAt, fallback: nil))
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // ── Presence + location ────────────────────
                        SystemsSection(title: "Presence", icon: "location.fill", accent: .cyan) {
                            SysRow(label: "Home Geofence") {
                                syncStatusChip(label: geofence.homeCoordinate == nil ? "Not Set" : "Configured")
                            }
                            SysRow(label: "At Home") {
                                Text(geofence.isHome ? "Yes" : "No")
                                    .foregroundStyle(.white)
                            }
                            SysRow(label: "Weather Location") {
                                syncStatusChip(label: locationStatusLabel(weatherLocation.authorizationStatus))
                            }
                            if let coordinate = geofence.homeCoordinate {
                                Text(String(format: "Home: %.4f, %.4f", coordinate.latitude, coordinate.longitude))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            if let appState {
                                SysRow(label: "Present Members") {
                                    Text("\(appState.presence.presentMembers.count)")
                                        .foregroundStyle(.white)
                                }
                            }
                        }

                        // ── App info ────────────────────────────────
                        SystemsSection(title: "Build", icon: "info.circle.fill", accent: steel) {
                            SysRow(label: "Version") {
                                versionChip(
                                    Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "—",
                                    build: Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "—"
                                )
                            }
                        }

                        // ── Links ────────────────────────────────────
                        SystemsSection(title: "Links", icon: "link", accent: steel) {
                            Link(destination: URL(string: JARVISEnvironment.baseURL.absoluteString)!) {
                                HStack {
                                    Label("Open JARVIS Web", systemImage: "safari")
                                        .foregroundStyle(steel)
                                    Spacer()
                                    Image(systemName: "arrow.up.right.square")
                                        .font(.caption).foregroundStyle(.secondary)
                                }
                            }
                        }

                        // ── About watermark ──────────────────────────
                        VStack(spacing: 3) {
                            Text("JARVIS")
                                .font(.system(size: 11, weight: .black))
                                .tracking(2)
                                .foregroundStyle(.white.opacity(0.3))
                            Text("JUST A RATHER VERY INTELLIGENT SYSTEM")
                                .font(.system(size: 8, weight: .medium))
                                .tracking(1)
                                .foregroundStyle(.white.opacity(0.18))
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.top, 10)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                }
            }
            .navigationTitle("Systems")
            .navigationBarTitleDisplayMode(.large)
            .task { await refreshSystems() }
            .refreshable { await refreshSystems() }
        }
    }

    // MARK: - Version chip

    private func versionChip(_ version: String, build: String) -> some View {
        Text("v\(version) · build \(build)")
            .font(.system(size: 10, weight: .semibold).monospaced())
            .foregroundStyle(steel)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(steel.opacity(0.1), in: Capsule())
    }

    // MARK: - Ping

    private func systemsMetric(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 12))
    }

    private func syncStatusChip(label: String) -> some View {
        Text(label)
            .font(.system(size: 10, weight: .semibold))
            .foregroundStyle(steel)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(steel.opacity(0.1), in: Capsule())
    }

    @ViewBuilder
    private func syncHealthRow(label: String, domain: AppStateSyncDomain) -> some View {
        SysRow(label: label) {
            VStack(alignment: .trailing, spacing: 2) {
                syncStatusChip(label: domain.synced ? "Mirrored" : "Not synced yet")
                if let syncedAt = domain.syncedAt, !syncedAt.isEmpty {
                    Text(syncedAt)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    private func refreshSystems() async {
        isRefreshing = true
        defer { isRefreshing = false }
        do {
            async let status = AppleAPIClient.shared.fetchStatus()
            async let state = AppleAPIClient.shared.fetchAppState()
            watchStatus = try await status
            appState = try await state
            serverOK = true
            pingError = nil
        } catch {
            serverOK = false
            pingError = error.localizedDescription
        }
    }

    private func refreshEventSync() async {
        await eventSync.syncAll()
        await refreshSystems()
    }

    private func refreshHealthSync() async {
        await healthSync.requestPermissionsAndSync()
        await refreshSystems()
    }

    private func eventKitStatusLabel(_ status: EKAuthorizationStatus) -> String {
        switch status {
        case .fullAccess, .writeOnly:
            return "Connected"
        case .denied, .restricted:
            return "Blocked"
        case .notDetermined:
            return "Not Asked"
        @unknown default:
            return "Unknown"
        }
    }

    private func locationStatusLabel(_ status: CLAuthorizationStatus) -> String {
        switch status {
        case .authorizedAlways, .authorizedWhenInUse:
            return "Allowed"
        case .denied, .restricted:
            return "Blocked"
        case .notDetermined:
            return "Not Asked"
        default:
            return "Unknown"
        }
    }

    private func formatDate(_ date: Date?) -> String {
        guard let date else { return "Never" }
        return date.formatted(date: .abbreviated, time: .shortened)
    }

    private func nonEmpty(_ value: String?, fallback: String?) -> String {
        let primary = (value ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        if !primary.isEmpty {
            let iso = ISO8601DateFormatter()
            if let date = iso.date(from: primary) {
                return date.formatted(date: .abbreviated, time: .shortened)
            }
            return primary
        }
        let secondary = (fallback ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        return secondary.isEmpty ? "Not synced yet" : secondary
    }
}

// MARK: - Section

private struct SystemsSection<Content: View>: View {
    let title: String
    let icon: String
    let accent: Color
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(accent)
                Text(title.uppercased())
                    .font(.system(size: 10, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(accent.opacity(0.8))
            }
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Row

private struct SysRow<Trailing: View>: View {
    let label: String
    @ViewBuilder let trailing: Trailing

    var body: some View {
        HStack {
            Text(label)
                .font(.subheadline).foregroundStyle(.white)
            Spacer()
            trailing.font(.subheadline)
        }
        .padding(.vertical, 2)
    }
}
#Preview { SettingsView() }
