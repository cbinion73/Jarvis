import SwiftUI
import EventKit
import CoreLocation
import JarvisKit

// MARK: - SettingsView  "Systems"

struct SettingsView: View {
    @Environment(\.openURL) private var openURL

    @ObservedObject private var eventSync = EventKitSyncManager.shared
    @ObservedObject private var healthSync = HealthSyncManager.shared
    @ObservedObject private var geofence = GeofenceManager.shared
    @ObservedObject private var weatherLocation = WeatherLocationProvider.shared

    @State private var serverOK = false
    @State private var watchStatus: WatchStatus?
    @State private var appState: AppStateOverview?
    @State private var calendarState: CalendarWorkflowOverview?
    @State private var remindersState: ReminderWorkflowOverview?
    @State private var pingError: String?
    @State private var isRefreshing = false
    @State private var showingInbox = false
    @State private var calendarWorkflowMessage = ""
    @State private var calendarWorkflowError = ""
    @State private var reminderWorkflowMessage = ""
    @State private var reminderWorkflowError = ""

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
                            if let postureLabel = appState?.focus.postureLabel, !postureLabel.isEmpty {
                                SysRow(label: "Posture") {
                                    syncStatusChip(label: postureLabel)
                                }
                            }
                            if let recommendedDelivery = appState?.focus.recommendedDelivery, !recommendedDelivery.isEmpty {
                                SysRow(label: "Delivery") {
                                    Text(readableDeliveryMode(recommendedDelivery))
                                        .foregroundStyle(.white)
                                }
                            }
                            if let postureReason = appState?.focus.postureReason, !postureReason.isEmpty {
                                Text(postureReason)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
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
                                Button {
                                    showingInbox = true
                                } label: {
                                    Label("Open Notification Center", systemImage: "tray.full")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.yellow)
                                }
                                .buttonStyle(.plain)

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
                                            if let decisionReason = notification.decisionReason, !decisionReason.isEmpty {
                                                Text(decisionReason)
                                                    .font(.caption2)
                                                    .foregroundStyle(.yellow.opacity(0.8))
                                            }
                                            if !notification.createdAt.isEmpty {
                                                Text(nonEmpty(notification.createdAt, fallback: nil))
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        SystemsSection(title: "Calendar Workflow", icon: "calendar.badge.clock", accent: .cyan) {
                            if let calendarState {
                                SysRow(label: "Mirror") {
                                    syncStatusChip(label: calendarState.synced ? "Live" : "Not synced yet")
                                }
                                SysRow(label: "Events") {
                                    Text("\(calendarState.count)")
                                        .foregroundStyle(.white)
                                }
                                SysRow(label: "Synced At") {
                                    Text(nonEmpty(calendarState.syncedAt, fallback: nil))
                                        .foregroundStyle(.white)
                                }

                                if !calendarWorkflowError.isEmpty {
                                    Text(calendarWorkflowError)
                                        .font(.caption)
                                        .foregroundStyle(.red.opacity(0.9))
                                } else if !calendarWorkflowMessage.isEmpty {
                                    Text(calendarWorkflowMessage)
                                        .font(.caption)
                                        .foregroundStyle(.cyan.opacity(0.9))
                                }

                                if !calendarState.attentionFlags.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Attention Flags")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(calendarState.attentionFlags.prefix(3)) { flag in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(flag.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: flag.severity.capitalized)
                                                }
                                                Text(flag.detail)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                            }
                                        }
                                    }
                                }

                                if !calendarState.nextEvents.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Next Events")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 10) {
                                        ForEach(calendarState.nextEvents.prefix(3)) { event in
                                            VStack(alignment: .leading, spacing: 5) {
                                                Text(event.title.isEmpty ? "Upcoming event" : event.title)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                Text(calendarTimingLabel(for: event))
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                if !event.location.isEmpty {
                                                    Text(event.location)
                                                        .font(.caption2)
                                                        .foregroundStyle(.cyan.opacity(0.8))
                                                }
                                                HStack(spacing: 10) {
                                                    Button("Stage Prep") {
                                                        Task { await prepareCalendarEvent(event) }
                                                    }
                                                    .buttonStyle(.borderedProminent)
                                                    .tint(.cyan)

                                                    if event.routeReady {
                                                        Button("Route") {
                                                            openCalendarRoute(for: event)
                                                        }
                                                        .buttonStyle(.bordered)
                                                        .tint(.white.opacity(0.85))
                                                    }
                                                }
                                                .font(.caption.weight(.semibold))
                                            }
                                        }
                                    }
                                }

                                if !calendarState.preparationCues.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Preparation Cues")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 6) {
                                        ForEach(calendarState.preparationCues.prefix(3)) { cue in
                                            VStack(alignment: .leading, spacing: 3) {
                                                Text(cue.title)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                Text(cue.detail)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                            }
                                        }
                                    }
                                }
                            } else {
                                Text("Calendar workflow not loaded yet.")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }

                        SystemsSection(title: "Reminder Workflow", icon: "checklist.checked", accent: .orange) {
                            if let remindersState {
                                SysRow(label: "Mirror") {
                                    syncStatusChip(label: remindersState.synced ? "Live" : "Not synced yet")
                                }
                                SysRow(label: "Open") {
                                    Text("\(remindersState.count)")
                                        .foregroundStyle(.white)
                                }
                                SysRow(label: "Synced At") {
                                    Text(nonEmpty(remindersState.syncedAt, fallback: nil))
                                        .foregroundStyle(.white)
                                }

                                if !reminderWorkflowError.isEmpty {
                                    Text(reminderWorkflowError)
                                        .font(.caption)
                                        .foregroundStyle(.red.opacity(0.9))
                                } else if !reminderWorkflowMessage.isEmpty {
                                    Text(reminderWorkflowMessage)
                                        .font(.caption)
                                        .foregroundStyle(.orange.opacity(0.95))
                                }

                                if !remindersState.attentionFlags.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Attention Flags")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(remindersState.attentionFlags.prefix(3)) { flag in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(flag.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: flag.severity.capitalized)
                                                }
                                                Text(flag.detail)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                            }
                                        }
                                    }
                                }

                                if !remindersState.overdueItems.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Overdue")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    reminderWorkflowList(remindersState.overdueItems.prefix(3))
                                } else if !remindersState.dueSoonItems.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Due Soon")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    reminderWorkflowList(remindersState.dueSoonItems.prefix(3))
                                } else if !remindersState.priorityItems.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Priority")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    reminderWorkflowList(remindersState.priorityItems.prefix(3))
                                } else if !remindersState.openItems.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Open Queue")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    reminderWorkflowList(remindersState.openItems.prefix(3))
                                }
                            } else {
                                Text("Reminder workflow not loaded yet.")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
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
            .sheet(isPresented: $showingInbox) {
                NotificationCenterView()
            }
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
            async let calendar = AppleAPIClient.shared.fetchCalendarState()
            async let reminders = AppleAPIClient.shared.fetchRemindersState()
            watchStatus = try await status
            appState = try await state
            calendarState = try await calendar
            remindersState = try await reminders
            serverOK = true
            pingError = nil
            calendarWorkflowError = ""
            reminderWorkflowError = ""
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

    private func readableDeliveryMode(_ mode: String) -> String {
        switch mode {
        case "deliver_now":
            return "Deliver Now"
        case "hold_for_brief":
            return "Hold for Brief"
        case "quiet_store":
            return "Quiet Store"
        case "badge_only":
            return "Badge Only"
        default:
            return mode.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }

    private func calendarTimingLabel(for event: CalendarWorkflowEvent) -> String {
        if let minutesAway = event.minutesAway {
            if minutesAway < 0 {
                return "Started \(abs(minutesAway)) min ago"
            }
            return "Starts in \(minutesAway) min"
        }
        return nonEmpty(event.start, fallback: "Time not available")
    }

    private func prepareCalendarEvent(_ event: CalendarWorkflowEvent) async {
        calendarWorkflowError = ""
        do {
            if try await AppleAPIClient.shared.prepareCalendarEvent(event.id) {
                calendarWorkflowMessage = "Staged prep for \(event.title)"
                calendarState = try await AppleAPIClient.shared.fetchCalendarState()
            }
        } catch {
            calendarWorkflowError = error.localizedDescription
        }
    }

    private func openCalendarRoute(for event: CalendarWorkflowEvent) {
        let destination = event.location.isEmpty ? event.title : event.location
        let query = destination.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? destination
        guard let url = URL(string: "http://maps.apple.com/?daddr=\(query)&dirflg=d") else { return }
        openURL(url)
    }

    @ViewBuilder
    private func reminderWorkflowList<S: Sequence>(_ items: S) -> some View where S.Element == ReminderWorkflowItem {
        VStack(alignment: .leading, spacing: 10) {
            ForEach(Array(items), id: \.id) { item in
                VStack(alignment: .leading, spacing: 5) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(item.title.isEmpty ? "Reminder" : item.title)
                            .font(.caption.bold())
                            .foregroundStyle(.white)
                        Spacer()
                        syncStatusChip(label: item.priorityLabel.capitalized)
                    }
                    Text(reminderTimingLabel(for: item))
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    if !item.list.isEmpty {
                        Text(item.list)
                            .font(.caption2)
                            .foregroundStyle(.orange.opacity(0.85))
                    }
                    HStack(spacing: 10) {
                        Button("Complete") {
                            Task { await completeReminderWorkflow(item) }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(.orange)

                        Button("Snooze 1h") {
                            Task { await snoozeReminderWorkflow(item) }
                        }
                        .buttonStyle(.bordered)
                        .tint(.white.opacity(0.85))
                    }
                    .font(.caption.weight(.semibold))
                }
            }
        }
    }

    private func reminderTimingLabel(for item: ReminderWorkflowItem) -> String {
        if let minutesAway = item.minutesAway {
            if minutesAway < 0 {
                return "Overdue by \(abs(minutesAway)) min"
            }
            return "Due in \(minutesAway) min"
        }
        return nonEmpty(item.due, fallback: "No due date")
    }

    private func completeReminderWorkflow(_ item: ReminderWorkflowItem) async {
        reminderWorkflowError = ""
        do {
            if try await AppleAPIClient.shared.completeReminder(item.id) {
                reminderWorkflowMessage = "Completed \(item.title)"
                remindersState = try await AppleAPIClient.shared.fetchRemindersState()
                appState = try await AppleAPIClient.shared.fetchAppState()
            }
        } catch {
            reminderWorkflowError = error.localizedDescription
        }
    }

    private func snoozeReminderWorkflow(_ item: ReminderWorkflowItem) async {
        reminderWorkflowError = ""
        do {
            if try await AppleAPIClient.shared.snoozeReminder(item.id, minutes: 60) {
                reminderWorkflowMessage = "Snoozed \(item.title) for 1 hour"
                remindersState = try await AppleAPIClient.shared.fetchRemindersState()
                appState = try await AppleAPIClient.shared.fetchAppState()
            }
        } catch {
            reminderWorkflowError = error.localizedDescription
        }
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

private extension View {
    @ViewBuilder
    func applyNotificationButtonStyle(prominent: Bool) -> some View {
        if prominent {
            self.buttonStyle(.borderedProminent)
        } else {
            self.buttonStyle(.bordered)
        }
    }
}

#Preview { SettingsView() }

struct NotificationCenterView: View {
    @Environment(\.dismiss) private var dismiss

    @State private var notifications: [NotificationCenterItem] = []
    @State private var events: [EventTimelineItem] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var notificationSearchText = ""
    @State private var eventSearchText = ""
    @State private var selectedNotificationStatus = "all"
    @State private var selectedNotificationCategory = "all"
    @State private var selectedNotificationSeverity = "all"
    @State private var selectedEventDomain = "all"

    private let client = AppleAPIClient.shared
    private let accent = Color(red: 1.0, green: 0.82, blue: 0.28)
    private var notificationStatuses: [String] {
        ["all"] + notifications.map { $0.status.lowercased() }.filter { !$0.isEmpty }.uniqued()
    }
    private var notificationCategories: [String] {
        ["all"] + notifications.map { $0.category.lowercased() }.filter { !$0.isEmpty }.uniqued()
    }
    private var notificationSeverities: [String] {
        ["all"] + notifications.map { $0.severity.lowercased() }.filter { !$0.isEmpty }.uniqued()
    }
    private var eventDomains: [String] {
        ["all"] + events.map { $0.domain.lowercased() }.filter { !$0.isEmpty }.uniqued()
    }
    private var filteredNotifications: [NotificationCenterItem] {
        notifications.filter { item in
            let matchesQuery = notificationSearchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                || notificationSearchHaystack(for: item).localizedCaseInsensitiveContains(notificationSearchText)
            return (selectedNotificationStatus == "all" || item.status.lowercased() == selectedNotificationStatus) &&
                (selectedNotificationCategory == "all" || item.category.lowercased() == selectedNotificationCategory) &&
                (selectedNotificationSeverity == "all" || item.severity.lowercased() == selectedNotificationSeverity) &&
                matchesQuery
        }
    }
    private var filteredEvents: [EventTimelineItem] {
        events.filter { item in
            let matchesQuery = eventSearchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                || eventSearchHaystack(for: item).localizedCaseInsensitiveContains(eventSearchText)
            return (selectedEventDomain == "all" || item.domain.lowercased() == selectedEventDomain) && matchesQuery
        }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                Group {
                    if isLoading && notifications.isEmpty && events.isEmpty {
                        ProgressView("Loading Inbox…")
                            .tint(accent)
                    } else {
                        ScrollView {
                            VStack(spacing: 14) {
                                if let errorMessage, !errorMessage.isEmpty {
                                    Text(errorMessage)
                                        .font(.caption)
                                        .foregroundStyle(.red.opacity(0.9))
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .padding(12)
                                        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
                                }

                                HStack(spacing: 10) {
                                    summaryMetric(title: "Pending", value: "\(notifications.filter { $0.status == "pending" }.count)")
                                    summaryMetric(title: "Active", value: "\(notifications.count)")
                                    summaryMetric(title: "Events", value: "\(events.count)")
                                }
                                .padding(12)
                                .glassEffect(in: RoundedRectangle(cornerRadius: 18))

                                if notifications.isEmpty {
                                    VStack(spacing: 8) {
                                        Image(systemName: "bell.slash")
                                            .font(.system(size: 28))
                                            .foregroundStyle(accent.opacity(0.8))
                                        Text("No active notifications")
                                            .font(.headline)
                                            .foregroundStyle(.white)
                                        Text("JARVIS does not currently have any unresolved household attention items.")
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                            .multilineTextAlignment(.center)
                                    }
                                    .padding(18)
                                    .frame(maxWidth: .infinity)
                                    .glassEffect(in: RoundedRectangle(cornerRadius: 20))
                                } else {
                                    VStack(alignment: .leading, spacing: 10) {
                                        sectionHeader("Inbox", icon: "bell.badge.fill")
                                        filterSearchField(
                                            title: "Search notifications",
                                            text: $notificationSearchText,
                                            prompt: "Search title, detail, or reason"
                                        )
                                        filterScroller(
                                            title: "Status",
                                            values: notificationStatuses,
                                            selected: selectedNotificationStatus
                                        ) { selectedNotificationStatus = $0 }
                                        filterScroller(
                                            title: "Category",
                                            values: notificationCategories,
                                            selected: selectedNotificationCategory
                                        ) { selectedNotificationCategory = $0 }
                                        filterScroller(
                                            title: "Severity",
                                            values: notificationSeverities,
                                            selected: selectedNotificationSeverity
                                        ) { selectedNotificationSeverity = $0 }
                                        Text("Showing \(filteredNotifications.count) of \(notifications.count)")
                                            .font(.caption2)
                                            .foregroundStyle(.secondary)
                                        if filteredNotifications.isEmpty {
                                            emptyFilterState("No notifications match the current filters.")
                                        }
                                        ForEach(filteredNotifications) { item in
                                            VStack(alignment: .leading, spacing: 8) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(item.title.isEmpty ? "JARVIS Alert" : item.title)
                                                        .font(.headline)
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    pill(item.severity.uppercased(), color: severityColor(item.severity))
                                                }

                                                if !item.detail.isEmpty {
                                                    Text(item.detail)
                                                        .font(.caption)
                                                        .foregroundStyle(.secondary)
                                                }

                                                HStack(spacing: 8) {
                                                    if !item.category.isEmpty {
                                                        pill(item.category.capitalized, color: accent)
                                                    }
                                                    if !item.status.isEmpty {
                                                        pill(item.status.capitalized, color: .white.opacity(0.35))
                                                    }
                                                }

                                                if !item.whyNow.isEmpty {
                                                    Text(item.whyNow)
                                                        .font(.caption2)
                                                        .foregroundStyle(accent.opacity(0.85))
                                                }

                                                if let decisionReason = item.decisionReason, !decisionReason.isEmpty {
                                                    Text(decisionReason)
                                                        .font(.caption2)
                                                        .foregroundStyle(.yellow.opacity(0.8))
                                                }

                                                HStack(spacing: 8) {
                                                    pill(readableDeliveryMode(item.deliveryMode), color: .blue.opacity(0.82))
                                                    if let postureLabel = item.postureSnapshot?.label, !postureLabel.isEmpty {
                                                        pill(postureLabel, color: .white.opacity(0.35))
                                                    }
                                                }

                                                HStack(spacing: 10) {
                                                    ForEach(buttonActions(for: item), id: \.self) { action in
                                                        Button(notificationActionLabel(action)) {
                                                            Task { await performAction(action, for: item.id) }
                                                        }
                                                        .tint(buttonTint(for: action))
                                                        .applyNotificationButtonStyle(prominent: isProminentAction(action))
                                                    }
                                                }
                                                .font(.caption.weight(.semibold))

                                                Text(formatTimestamp(item.createdAt))
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary.opacity(0.75))
                                            }
                                            .padding(14)
                                            .glassEffect(in: RoundedRectangle(cornerRadius: 18))
                                        }
                                    }
                                }

                                if !events.isEmpty {
                                    VStack(alignment: .leading, spacing: 10) {
                                        sectionHeader("Recent Events", icon: "clock.arrow.circlepath")
                                        filterSearchField(
                                            title: "Search event spine",
                                            text: $eventSearchText,
                                            prompt: "Search title, detail, or domain"
                                        )
                                        filterScroller(
                                            title: "Domain",
                                            values: eventDomains,
                                            selected: selectedEventDomain
                                        ) { selectedEventDomain = $0 }
                                        Text("Showing \(filteredEvents.count) of \(events.count)")
                                            .font(.caption2)
                                            .foregroundStyle(.secondary)
                                        if filteredEvents.isEmpty {
                                            emptyFilterState("No recent events match the current filters.")
                                        }
                                        ForEach(filteredEvents.prefix(8)) { event in
                                            VStack(alignment: .leading, spacing: 5) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(event.title)
                                                        .font(.subheadline.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    pill(event.domain.uppercased(), color: .blue.opacity(0.8))
                                                }
                                                if !event.detail.isEmpty {
                                                    Text(event.detail)
                                                        .font(.caption)
                                                        .foregroundStyle(.secondary)
                                                        .lineLimit(3)
                                                }
                                                if !event.whyNow.isEmpty {
                                                    Text(event.whyNow)
                                                        .font(.caption2)
                                                        .foregroundStyle(accent.opacity(0.85))
                                                }
                                                Text(formatTimestamp(event.ts))
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary.opacity(0.75))
                                            }
                                            .padding(12)
                                            .glassEffect(in: RoundedRectangle(cornerRadius: 16))
                                        }
                                    }
                                }
                            }
                            .padding()
                        }
                    }
                }
            }
            .navigationTitle("Notification Center")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Done") { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await load() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                }
            }
        }
        .task { await load() }
    }

    private func load() async {
        isLoading = true
        errorMessage = nil
        do {
            async let fetchedNotifications = client.fetchNotifications()
            async let fetchedEvents = client.fetchRecentEvents(limit: 20)
            notifications = try await fetchedNotifications
            events = try await fetchedEvents
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func markSeen(_ id: String) async {
        do {
            if try await client.markNotificationSeen(id) {
                await load()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func dismissNotification(_ id: String) async {
        do {
            if try await client.dismissNotification(id) {
                await load()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func resolveNotification(_ id: String) async {
        do {
            if try await client.resolveNotification(id) {
                await load()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func performAction(_ action: String, for id: String) async {
        switch action {
        case "seen":
            await markSeen(id)
        case "dismiss":
            await dismissNotification(id)
        case "resolve":
            await resolveNotification(id)
        case "snooze":
            do {
                if try await client.snoozeNotification(id) {
                    await load()
                }
            } catch {
                errorMessage = error.localizedDescription
            }
        default:
            do {
                if try await client.performNotificationAction(id, action: action) {
                    await load()
                }
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }

    private func summaryMetric(title: String, value: String) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.headline)
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }

    private func sectionHeader(_ title: String, icon: String) -> some View {
        HStack {
            Label(title, systemImage: icon)
                .font(.headline)
                .foregroundStyle(.white)
            Spacer()
        }
    }

    private func pill(_ text: String, color: Color) -> some View {
        Text(text)
            .font(.system(size: 9, weight: .black))
            .tracking(0.8)
            .foregroundStyle(.black)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(color, in: Capsule())
    }

    private func severityColor(_ severity: String) -> Color {
        switch severity.lowercased() {
        case "critical":
            return .red
        case "high":
            return .orange
        case "medium":
            return .yellow
        default:
            return .white.opacity(0.75)
        }
    }

    private func buttonActions(for item: NotificationCenterItem) -> [String] {
        let allowed = item.availableActions.filter { !$0.isEmpty && $0 != "open" }
        return allowed.isEmpty ? ["seen", "dismiss", "resolve"] : allowed
    }

    private func notificationActionLabel(_ action: String) -> String {
        switch action {
        case "complete_reminder":
            return "Complete"
        case "snooze_reminder":
            return "Snooze 1h"
        case "stage_prep":
            return "Stage Prep"
        default:
            return action.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }

    private func buttonTint(for action: String) -> Color {
        switch action {
        case "dismiss":
            return .orange
        case "resolve", "complete_reminder", "stage_prep":
            return accent
        default:
            return .white.opacity(0.8)
        }
    }

    private func isProminentAction(_ action: String) -> Bool {
        ["resolve", "complete_reminder", "stage_prep"].contains(action)
    }

    private func notificationSearchHaystack(for item: NotificationCenterItem) -> String {
        [
            item.title,
            item.detail,
            item.whyNow,
            item.category,
            item.status,
            item.severity,
            item.decisionReason ?? "",
            item.deliveryMode,
            item.postureSnapshot?.label ?? ""
        ]
        .joined(separator: " ")
    }

    private func eventSearchHaystack(for item: EventTimelineItem) -> String {
        [
            item.title,
            item.detail,
            item.whyNow,
            item.domain,
            item.severity
        ]
        .joined(separator: " ")
    }

    private func filterScroller(
        title: String,
        values: [String],
        selected: String,
        onSelect: @escaping (String) -> Void
    ) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.secondary)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(values, id: \.self) { value in
                        Button(prettyFilterLabel(value)) {
                            onSelect(value)
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(selected == value ? accent : .white.opacity(0.18))
                        .foregroundStyle(selected == value ? .black : .white)
                    }
                }
            }
        }
    }

    private func emptyFilterState(_ message: String) -> some View {
        Text(message)
            .font(.caption)
            .foregroundStyle(.secondary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 6)
    }

    private func filterSearchField(title: String, text: Binding<String>, prompt: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.secondary)
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)
                TextField(prompt, text: text)
                    .textInputAutocapitalization(.never)
                    .disableAutocorrection(true)
                    .foregroundStyle(.white)
                if !text.wrappedValue.isEmpty {
                    Button {
                        text.wrappedValue = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(Color.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        }
    }

    private func prettyFilterLabel(_ raw: String) -> String {
        if raw == "all" { return "All" }
        return raw.replacingOccurrences(of: "_", with: " ").capitalized
    }

    private func formatTimestamp(_ raw: String) -> String {
        guard !raw.isEmpty else { return "Just now" }
        let formatter = ISO8601DateFormatter()
        guard let date = formatter.date(from: raw) else { return raw }
        return date.formatted(date: .abbreviated, time: .shortened)
    }

    private func readableDeliveryMode(_ mode: String) -> String {
        switch mode {
        case "deliver_now":
            return "Deliver Now"
        case "hold_for_brief":
            return "Hold for Brief"
        case "quiet_store":
            return "Quiet Store"
        case "badge_only":
            return "Badge Only"
        default:
            return mode.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }
}

private extension Array where Element == String {
    func uniqued() -> [String] {
        var seen = Set<String>()
        return filter { seen.insert($0).inserted }
    }
}
