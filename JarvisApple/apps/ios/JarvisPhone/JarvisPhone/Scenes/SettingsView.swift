import SwiftUI
import EventKit
import CoreLocation
import UserNotifications
import UIKit
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
    @State private var focusState: FocusStateOverview?
    @State private var soundHistory: SoundHistoryOverview?
    @State private var visionHistory: VisionHistoryOverview?
    @State private var nowPlayingState: NowPlayingStateOverview?
    @State private var controlPlane: ControlPlaneOverview?
    @State private var adminSummary: SystemsAdminSummary?
    @State private var notificationAuthorizationStatus: UNAuthorizationStatus = .notDetermined
    @State private var remoteNotificationsRegistered = false
    @State private var pingError: String?
    @State private var isRefreshing = false
    @State private var refreshGeneration = 0
    @State private var showingInbox = false
    @State private var calendarWorkflowMessage = ""
    @State private var calendarWorkflowError = ""
    @State private var reminderWorkflowMessage = ""
    @State private var reminderWorkflowError = ""
    @State private var focusWorkflowMessage = ""
    @State private var focusWorkflowError = ""
    @State private var focusPresetInFlight: String?
    @State private var signalWorkflowMessage = ""
    @State private var signalWorkflowError = ""
    @State private var governanceWorkflowMessage = ""
    @State private var governanceWorkflowError = ""
    @State private var governanceActionInFlight: String?
    @State private var adminSummaryDiagnostics = "Idle"

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
                                if adminSummary == nil {
                                    Text("Admin fetch: \(adminSummaryDiagnostics)")
                                        .font(.caption2.monospaced())
                                        .foregroundStyle(.secondary)
                                        .lineLimit(2)
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

                        if let adminSummary {
                            SystemsSection(title: "Governed", icon: "point.3.connected.trianglepath.dotted", accent: .teal) {
                                HStack(spacing: 10) {
                                    systemsMetric("Pending", "\(adminSummary.governedWorkflows.pendingApprovalCount)")
                                    systemsMetric("Lane Reviews", "\(adminSummary.governedWorkflows.stagedStewardshipReviewCount)")
                                    systemsMetric("Routes", "\(adminSummary.governedWorkflows.stagedCalendarRouteCount)")
                                    systemsMetric("Rules", "\(adminSummary.governedWorkflows.activeRuleCount)")
                                }
                                if let route = adminSummary.governedWorkflows.recentCalendarRoutes.first {
                                    SysRow(label: "Top Route Lane") {
                                        VStack(alignment: .trailing, spacing: 2) {
                                            Text(route.title)
                                                .foregroundStyle(.white)
                                                .lineLimit(1)
                                            Text(route.status.replacingOccurrences(of: "_", with: " ").capitalized)
                                                .font(.caption2)
                                                .foregroundStyle(.secondary)
                                        }
                                    }
                                }
                                if let review = adminSummary.governedWorkflows.recentStewardshipReviews.first {
                                    SysRow(label: "Top Review Lane") {
                                        VStack(alignment: .trailing, spacing: 2) {
                                            Text(review.laneTitle)
                                                .foregroundStyle(.white)
                                                .lineLimit(1)
                                            Text(review.status.replacingOccurrences(of: "_", with: " ").capitalized)
                                                .font(.caption2)
                                                .foregroundStyle(.secondary)
                                        }
                                    }
                                }
                            }
                        }

                        // ── Server environment ──────────────────────
                        SystemsSection(title: "Server", icon: "wifi", accent: steel) {
                            HStack {
                                Text("Environment")
                                    .font(.caption).foregroundStyle(.secondary)
                                Spacer()
                                Text(JARVISEnvironment.environmentLabel)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(JARVISEnvironment.isOverrideActive ? .yellow : .green)
                            }

                            Text(JARVISEnvironment.environmentSummary)
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

                            if adminSummary == nil {
                                Divider().opacity(0.3)
                                SysRow(label: "Admin Fetch") {
                                    Text(adminSummaryDiagnostics)
                                        .font(.caption2.monospaced())
                                        .foregroundStyle(.white)
                                        .multilineTextAlignment(.trailing)
                                        .lineLimit(3)
                                }
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

                        SystemsSection(title: "Admin", icon: "slider.horizontal.3", accent: .teal) {
                            if let adminSummary {
                                HStack(spacing: 10) {
                                    systemsMetric("Accounts", "\(adminSummary.accounts.connected)/\(adminSummary.accounts.total)")
                                    systemsMetric("Family", "\(adminSummary.family.onlineCount)/\(adminSummary.family.memberCount)")
                                    systemsMetric("Devices", "\(adminSummary.devices.mappedCount)/\(adminSummary.devices.total)")
                                }

                                Divider().opacity(0.3)
                                SysRow(label: "Voice Stack") {
                                    syncStatusChip(label: adminSummary.voice.providerLabel)
                                }
                                SysRow(label: "Voice Readiness") {
                                    Text(adminSummary.voice.detail)
                                        .foregroundStyle(.white)
                                        .lineLimit(2)
                                        .multilineTextAlignment(.trailing)
                                }
                                SysRow(label: "Google") {
                                    Text("\(adminSummary.integrations.googleConnectedCount) connected")
                                        .foregroundStyle(.white)
                                }
                                SysRow(label: "Microsoft") {
                                    Text("\(adminSummary.integrations.microsoftConnectedCount) connected")
                                        .foregroundStyle(.white)
                                }
                                SysRow(label: "Runtime Host") {
                                    Text(adminSummary.service.hostname.isEmpty ? "jarvis.local" : adminSummary.service.hostname)
                                        .foregroundStyle(.white)
                                }
                                SysRow(label: "Deployment") {
                                    Text(adminSummary.service.modeLabel.isEmpty ? "Hybrid household plus hosted edge" : adminSummary.service.modeLabel)
                                        .foregroundStyle(.white)
                                        .multilineTextAlignment(.trailing)
                                }
                                SysRow(label: "Hosted Edge") {
                                    Text("\(adminSummary.service.hostedProvider) via \(adminSummary.service.edgeProvider)")
                                        .foregroundStyle(.white)
                                        .multilineTextAlignment(.trailing)
                                }
                                SysRow(label: "Hosted URL") {
                                    Text(adminSummary.service.hostedBaseURL.isEmpty ? "https://jarvis.teambinion.org" : adminSummary.service.hostedBaseURL)
                                        .foregroundStyle(.white)
                                        .multilineTextAlignment(.trailing)
                                }
                                SysRow(label: "Edge Posture") {
                                    Text("\(adminSummary.service.cloudflareAccessEnabled ? "Access protected" : "Open edge") · \(adminSummary.service.tunnelEnabled ? "Tunnel enabled" : "Tunnel off")")
                                        .foregroundStyle(.white)
                                        .multilineTextAlignment(.trailing)
                                }
                                SysRow(label: "Remote Admin") {
                                    Text(adminSummary.service.remoteAdminHost.isEmpty ? "Not set" : adminSummary.service.remoteAdminHost)
                                        .foregroundStyle(.white)
                                        .multilineTextAlignment(.trailing)
                                }
                                SysRow(label: "Hosted Routes") {
                                    Text("\(adminSummary.service.publicRouteCount) routes · \(adminSummary.service.composeServiceCount) services")
                                        .foregroundStyle(.white)
                                        .multilineTextAlignment(.trailing)
                                }

                                Divider().opacity(0.3)
                                Text("Accounts")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                VStack(alignment: .leading, spacing: 8) {
                                    ForEach(adminSummary.accounts.items.prefix(3)) { account in
                                        VStack(alignment: .leading, spacing: 3) {
                                            HStack(alignment: .firstTextBaseline) {
                                                Text(account.label.isEmpty ? account.id : account.label)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                Spacer()
                                                syncStatusChip(label: account.status.replacingOccurrences(of: "_", with: " ").capitalized)
                                            }
                                            Text("\(account.provider.capitalized) · \(account.detail)")
                                                .font(.caption2)
                                                .foregroundStyle(.secondary)
                                                .lineLimit(2)
                                        }
                                    }
                                }

                                Divider().opacity(0.3)
                                Text("Family + Devices")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                VStack(alignment: .leading, spacing: 8) {
                                    ForEach(adminSummary.family.members.prefix(3)) { member in
                                        VStack(alignment: .leading, spacing: 3) {
                                            HStack(alignment: .firstTextBaseline) {
                                                Text(member.displayName.isEmpty ? member.id : member.displayName)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                Spacer()
                                                syncStatusChip(label: member.status)
                                            }
                                            Text("\(member.role.isEmpty ? "Member" : member.role.capitalized) · \(member.onlineDeviceCount)/\(member.deviceCount) devices online")
                                                .font(.caption2)
                                                .foregroundStyle(.secondary)
                                        }
                                    }
                                }

                                Divider().opacity(0.3)
                                Text("AI Costs")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                HStack(spacing: 10) {
                                    systemsMetric("Month", adminCurrency(adminSummary.costs.monthTotalUSD))
                                    systemsMetric("Paid Calls", "\(adminSummary.costs.paidCalls)")
                                    systemsMetric("Tokens", shortTokenCount(adminSummary.costs.promptTokens + adminSummary.costs.completionTokens))
                                }
                                if let topModel = adminSummary.costs.models.first {
                                    Text("Top model: \(topModel.name) · \(topModel.calls) calls · \(adminCurrency(topModel.costUSD))")
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                }

                                Divider().opacity(0.3)
                                Text("Governance")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                HStack(spacing: 10) {
                                    systemsMetric("Zones", "\(adminSummary.governance.activeZoneCount)/\(adminSummary.governance.zoneCount)")
                                    systemsMetric("Arenas", "\(adminSummary.governance.activeArenaCount)/\(adminSummary.governance.arenaCount)")
                                    systemsMetric("Queue", "\(adminSummary.governance.pendingQueueCount)")
                                    systemsMetric("Ledger", "\(adminSummary.governance.promotionRecordCount)")
                                }
                                if !adminSummary.governance.zones.isEmpty {
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.governance.zones.prefix(3)) { zone in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(zone.name.isEmpty ? zone.id : zone.name)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: zone.status.capitalized)
                                                }
                                                Text("\(zone.zoneType.replacingOccurrences(of: "_", with: " ").capitalized) · \(zone.approvalMode.replacingOccurrences(of: "_", with: " ")) · \(zone.actionCount) actions")
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                Text("Stage · \(zone.authorityStage.replacingOccurrences(of: "_", with: " ").capitalized)")
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                HStack(spacing: 8) {
                                                    Button("Promote") {
                                                        Task { await promoteTrustZone(zone) }
                                                    }
                                                    .disabled(governanceActionInFlight != nil)
                                                    .buttonStyle(.plain)
                                                    .padding(.horizontal, 8)
                                                    .padding(.vertical, 4)
                                                    .background(steel.opacity(0.14), in: Capsule())

                                                    Button("Demote") {
                                                        Task { await demoteTrustZone(zone) }
                                                    }
                                                    .disabled(governanceActionInFlight != nil)
                                                    .buttonStyle(.plain)
                                                    .padding(.horizontal, 8)
                                                    .padding(.vertical, 4)
                                                    .background(Color.orange.opacity(0.16), in: Capsule())
                                                }
                                                .font(.caption2.weight(.semibold))
                                            }
                                        }
                                    }
                                }
                                if !adminSummary.governance.arenas.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Arenas")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.governance.arenas.prefix(2)) { arena in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(arena.name.isEmpty ? arena.id : arena.name)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: arena.riskClass.capitalized)
                                                }
                                                Text("\(arena.resourceType.replacingOccurrences(of: "_", with: " ").capitalized) · zone \(arena.linkedZoneId)")
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(2)
                                                HStack(spacing: 8) {
                                                    if arena.status.lowercased() == "suspended" {
                                                        Button("Resume") {
                                                            Task { await resumeResourceArena(arena) }
                                                        }
                                                        .disabled(governanceActionInFlight != nil)
                                                        .buttonStyle(.plain)
                                                        .padding(.horizontal, 8)
                                                        .padding(.vertical, 4)
                                                        .background(Color.green.opacity(0.16), in: Capsule())
                                                    } else {
                                                        Button("Suspend") {
                                                            Task { await suspendResourceArena(arena) }
                                                        }
                                                        .disabled(governanceActionInFlight != nil)
                                                        .buttonStyle(.plain)
                                                        .padding(.horizontal, 8)
                                                        .padding(.vertical, 4)
                                                        .background(Color.orange.opacity(0.16), in: Capsule())
                                                    }
                                                }
                                                .font(.caption2.weight(.semibold))
                                            }
                                        }
                                    }
                                }
                                if let leadingStage = adminSummary.governance.stages.first {
                                    Divider().opacity(0.3)
                                    Text("Authority Ladder")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    Text("\(leadingStage.name) starts the ladder, and \(adminSummary.governance.stageCount) authority stages are currently registered.")
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                }
                                if let queuedItem = adminSummary.governance.queue.first {
                                    Divider().opacity(0.3)
                                    Text("Stage Queue")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    Text("\(queuedItem.actionType.replacingOccurrences(of: "_", with: " ").capitalized) in \(queuedItem.arenaId) · \(queuedItem.status.replacingOccurrences(of: "_", with: " "))")
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                }
                                if !adminSummary.governance.promotionRecords.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Authority History")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.governance.promotionRecords.prefix(3)) { record in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text("\(record.eventType.replacingOccurrences(of: "_", with: " ").capitalized) · \(record.subjectKind.replacingOccurrences(of: "_", with: " "))")
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: record.status.capitalized)
                                                }
                                                Text(record.basis.isEmpty ? record.subjectId : record.basis)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(2)
                                                if !record.trustZone.isEmpty || !record.authorityStage.isEmpty {
                                                    Text("\(record.trustZone.isEmpty ? "shared-doctrine" : record.trustZone) · \(record.authorityStage.isEmpty ? "policy" : record.authorityStage)")
                                                        .font(.caption2)
                                                        .foregroundStyle(.secondary)
                                                }
                                            }
                                        }
                                    }
                                }
                                Divider().opacity(0.3)
                                Text("Sandbox Operations")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                HStack(spacing: 10) {
                                    systemsMetric("Active", "\(adminSummary.sandboxOperations.queue.activeCount)")
                                    systemsMetric("Sandbox Jobs", "\(adminSummary.sandboxOperations.queue.queuedJobCount)")
                                    systemsMetric("Review Ready", "\(adminSummary.sandboxOperations.queue.reviewReadyCount)")
                                    systemsMetric("Lanes", "\(adminSummary.sandboxOperations.queue.laneCount)")
                                }
                                if !adminSummary.sandboxOperations.laneSummaries.isEmpty {
                                    VStack(alignment: .leading, spacing: 8) {
                                        Text("Lane Posture")
                                            .font(.caption.weight(.semibold))
                                            .foregroundStyle(.secondary)
                                        ForEach(adminSummary.sandboxOperations.laneSummaries.prefix(3)) { lane in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(lane.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: lane.status.replacingOccurrences(of: "-", with: " ").capitalized)
                                                }
                                                Text(lane.detail)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(2)
                                                Text("Queued \(lane.queuedCount) · Active \(lane.activeRunCount) · Review ready \(lane.reviewReadyCount) · Failed \(lane.failedRunCount)")
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(1)
                                                if !lane.lastJobId.isEmpty {
                                                    Text("Latest job · \(lane.lastJobId)")
                                                        .font(.caption2)
                                                        .foregroundStyle(.secondary)
                                                        .lineLimit(1)
                                                }
                                            }
                                        }
                                    }
                                }
                                if !adminSummary.sandboxOperations.jobs.isEmpty {
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.sandboxOperations.jobs.prefix(2)) { job in
                                            VStack(alignment: .leading, spacing: 4) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(job.title.isEmpty ? job.id : job.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: job.status.replacingOccurrences(of: "_", with: " ").capitalized)
                                                }
                                                Text(job.summary.isEmpty ? job.jobType.replacingOccurrences(of: "-", with: " ").capitalized : job.summary)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(2)
                                                Text("\(job.target.isEmpty ? "general runtime" : job.target) · \(job.reviewLevel.replacingOccurrences(of: "-", with: " "))")
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(1)
                                                Button("Run in Sandbox") {
                                                    Task { await executeSandboxJob(job) }
                                                }
                                                .disabled(governanceActionInFlight != nil)
                                                .buttonStyle(.plain)
                                                .padding(.horizontal, 8)
                                                .padding(.vertical, 4)
                                                .background(Color.blue.opacity(0.16), in: Capsule())
                                                .font(.caption2.weight(.semibold))
                                                if job.status == "sandbox-queued" || job.status == "sandbox-running" || job.status == "sandbox-stop-requested" {
                                                    Button(job.status == "sandbox-stop-requested" ? "Stop Requested" : "Request Stop") {
                                                        Task { await cancelSandboxJob(job) }
                                                    }
                                                    .disabled(governanceActionInFlight != nil || job.status == "sandbox-stop-requested")
                                                    .buttonStyle(.plain)
                                                    .padding(.horizontal, 8)
                                                    .padding(.vertical, 4)
                                                    .background(Color.orange.opacity(0.16), in: Capsule())
                                                    .font(.caption2.weight(.semibold))
                                                }
                                                if job.status == "sandboxed" || job.status == "sandbox-cancelled" || job.status == "sandbox-failed" || job.status == "sandbox-reset" {
                                                    Button("Reset Lane") {
                                                        Task { await recoverSandboxJob(job) }
                                                    }
                                                    .disabled(governanceActionInFlight != nil)
                                                    .buttonStyle(.plain)
                                                    .padding(.horizontal, 8)
                                                    .padding(.vertical, 4)
                                                    .background(Color.red.opacity(0.16), in: Capsule())
                                                    .font(.caption2.weight(.semibold))
                                                }
                                            }
                                        }
                                    }
                                }
                                if let activeRun = adminSummary.sandboxOperations.activeRuns.first {
                                    Divider().opacity(0.3)
                                    Text("Active Sandbox Run")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 4) {
                                        HStack(alignment: .firstTextBaseline) {
                                            Text(activeRun.title.isEmpty ? activeRun.jobId : activeRun.title)
                                                .font(.caption.bold())
                                                .foregroundStyle(.white)
                                            Spacer()
                                            syncStatusChip(label: activeRun.status.replacingOccurrences(of: "_", with: " ").capitalized)
                                        }
                                        Text(activeRun.message)
                                            .font(.caption2)
                                            .foregroundStyle(.secondary)
                                            .lineLimit(2)
                                        if !activeRun.currentStep.isEmpty {
                                            Text("Step · \(activeRun.currentStep.replacingOccurrences(of: "-", with: " "))")
                                                .font(.caption2)
                                                .foregroundStyle(.secondary)
                                        }
                                    }
                                }
                                if let recentRun = adminSummary.sandboxOperations.recentRuns.first {
                                    Divider().opacity(0.3)
                                    Text("Latest Sandbox Report")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 4) {
                                        HStack(alignment: .firstTextBaseline) {
                                            Text(recentRun.title.isEmpty ? recentRun.jobId : recentRun.title)
                                                .font(.caption.bold())
                                                .foregroundStyle(.white)
                                            Spacer()
                                            syncStatusChip(label: recentRun.compileOK && recentRun.testsOK ? "Healthy" : "Needs review")
                                        }
                                        Text(recentRun.mode.replacingOccurrences(of: "-", with: " ").capitalized)
                                            .font(.caption2)
                                            .foregroundStyle(.secondary)
                                        if !recentRun.reportPath.isEmpty {
                                            Text(recentRun.reportPath)
                                                .font(.caption2.monospaced())
                                                .foregroundStyle(.secondary)
                                                .lineLimit(2)
                                                .truncationMode(.middle)
                                        }
                                    }
                                }
                                Divider().opacity(0.3)
                                Text("Reflective Memory")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                HStack(spacing: 10) {
                                    systemsMetric("Facts", "\(adminSummary.reflectiveMemory.profileFactCount)")
                                    systemsMetric("Proposals", "\(adminSummary.reflectiveMemory.pendingProposalCount)")
                                    systemsMetric("First Light", "\(adminSummary.reflectiveMemory.firstLightHistoryCount)")
                                    systemsMetric("Insights", "\(adminSummary.reflectiveMemory.activeInsightCount)/\(adminSummary.reflectiveMemory.insightCount)")
                                    systemsMetric("Stewardship", "\(adminSummary.reflectiveMemory.stewardshipDecisionCount)")
                                }
                                Text("\(adminSummary.reflectiveMemory.subjectDisplayName) · tone \(adminSummary.reflectiveMemory.preferredTone.isEmpty ? "default" : adminSummary.reflectiveMemory.preferredTone) · brief \(adminSummary.reflectiveMemory.briefingStyle.isEmpty ? "default" : adminSummary.reflectiveMemory.briefingStyle)")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(2)
                                if !adminSummary.reflectiveMemory.guidanceLines.isEmpty {
                                    VStack(alignment: .leading, spacing: 6) {
                                        ForEach(Array(adminSummary.reflectiveMemory.guidanceLines.prefix(3).enumerated()), id: \.offset) { _, line in
                                            Text(line)
                                                .font(.caption2)
                                                .foregroundStyle(.secondary)
                                                .lineLimit(2)
                                        }
                                    }
                                }
                                if !adminSummary.reflectiveMemory.profileFacts.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Durable Facts")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.reflectiveMemory.profileFacts.prefix(2)) { fact in
                                            VStack(alignment: .leading, spacing: 3) {
                                                Text(fact.title)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                Text(fact.summary)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(2)
                                                if !fact.tags.isEmpty {
                                                    Text(fact.tags.prefix(3).joined(separator: " · "))
                                                        .font(.caption2)
                                                        .foregroundStyle(.secondary)
                                                }
                                            }
                                        }
                                    }
                                }
                                if !adminSummary.reflectiveMemory.pendingProposals.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Memory Proposals")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.reflectiveMemory.pendingProposals.prefix(2)) { proposal in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(proposal.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: proposal.status.capitalized)
                                                }
                                                Text(proposal.summary)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(2)
                                                Text("\(proposal.memoryType.capitalized) · \(proposal.confidence.capitalized)")
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                            }
                                        }
                                    }
                                }
                                if !adminSummary.reflectiveMemory.recentFirstLight.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Recent First Light")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.reflectiveMemory.recentFirstLight.prefix(2)) { item in
                                            VStack(alignment: .leading, spacing: 3) {
                                                Text(item.label)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                Text(item.summary)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(2)
                                            }
                                        }
                                    }
                                }
                                if !adminSummary.reflectiveMemory.recentStewardshipDecisions.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Recent Stewardship Decisions")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.reflectiveMemory.recentStewardshipDecisions.prefix(2)) { item in
                                            VStack(alignment: .leading, spacing: 3) {
                                                Text(item.label)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                Text(item.summary)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(2)
                                            }
                                        }
                                    }
                                }
                                if !adminSummary.reflectiveMemory.governanceLearning.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Governance Learning")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    Text("\(adminSummary.reflectiveMemory.governanceLearningCount) synthesized governance learning item" + (adminSummary.reflectiveMemory.governanceLearningCount == 1 ? "" : "s"))
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.reflectiveMemory.governanceLearning.prefix(2)) { item in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(item.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: item.confidence.capitalized)
                                                }
                                                Text(item.summary)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(3)
                                                Text(item.recommendation)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(3)
                                            }
                                        }
                                    }
                                }
                                Divider().opacity(0.3)
                                Text("Memory Graph")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                HStack(spacing: 10) {
                                    systemsMetric("Anchors", "\(adminSummary.reflectiveMemory.memoryGraph.anchorCount)")
                                    systemsMetric("Threads", "\(adminSummary.reflectiveMemory.memoryGraph.threadCount)")
                                    systemsMetric("Horizons", "\(adminSummary.reflectiveMemory.memoryGraph.horizonCount)")
                                    systemsMetric("Coverage", "\(adminSummary.reflectiveMemory.memoryGraph.coverageCount)")
                                }
                                if !adminSummary.reflectiveMemory.memoryGraph.guidanceLines.isEmpty {
                                    VStack(alignment: .leading, spacing: 6) {
                                        ForEach(Array(adminSummary.reflectiveMemory.memoryGraph.guidanceLines.prefix(3).enumerated()), id: \.offset) { _, line in
                                            Text(line)
                                                .font(.caption2)
                                                .foregroundStyle(.secondary)
                                                .lineLimit(3)
                                        }
                                    }
                                }
                                if !adminSummary.reflectiveMemory.memoryGraph.activeThreads.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Active Threads")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.reflectiveMemory.memoryGraph.activeThreads.prefix(2)) { thread in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(thread.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: thread.horizon.uppercased())
                                                }
                                                Text(thread.summary)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(3)
                                                Text("\(thread.signalCount) signal" + (thread.signalCount == 1 ? "" : "s"))
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                            }
                                        }
                                    }
                                }
                                if !adminSummary.reflectiveMemory.memoryGraph.horizons.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Long Horizons")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.reflectiveMemory.memoryGraph.horizons.prefix(2)) { horizon in
                                            VStack(alignment: .leading, spacing: 3) {
                                                Text(horizon.label)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                Text(horizon.summary)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(3)
                                            }
                                        }
                                    }
                                }
                                if !governanceWorkflowMessage.isEmpty {
                                    Text(governanceWorkflowMessage)
                                        .font(.caption2)
                                        .foregroundStyle(.green)
                                }
                                if !governanceWorkflowError.isEmpty {
                                    Text(governanceWorkflowError)
                                        .font(.caption2)
                                        .foregroundStyle(.red)
                                }

                                Divider().opacity(0.3)
                                Text("Governed Workflows")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                HStack(spacing: 10) {
                                    systemsMetric("Pending", "\(adminSummary.governedWorkflows.pendingApprovalCount)")
                                    systemsMetric("Auto", "\(adminSummary.governedWorkflows.automaticActionCount)")
                                    systemsMetric("Lane Reviews", "\(adminSummary.governedWorkflows.stagedStewardshipReviewCount)")
                                    systemsMetric("Routes", "\(adminSummary.governedWorkflows.stagedCalendarRouteCount)")
                                    systemsMetric("Gov Props", "\(adminSummary.governedWorkflows.governanceProposalCount)")
                                    systemsMetric("Rules", "\(adminSummary.governedWorkflows.activeRuleCount)")
                                }
                                if !adminSummary.governedWorkflows.pendingApprovals.isEmpty {
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.governedWorkflows.pendingApprovals.prefix(2)) { approval in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(approval.actor.isEmpty ? "Approval" : approval.actor)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: approval.status.capitalized)
                                                }
                                                Text(approval.request)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(2)
                                            }
                                        }
                                    }
                                }
                                if !adminSummary.governedWorkflows.recentStewardshipReviews.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Stewardship Reviews")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.governedWorkflows.recentStewardshipReviews.prefix(2)) { review in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(review.laneTitle)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: review.status.replacingOccurrences(of: "_", with: " ").capitalized)
                                                }
                                                Text(review.boundaryReason.isEmpty ? review.reviewSurface.capitalized : review.boundaryReason)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(2)
                                                Text("\(review.packetTarget.capitalized) · \(review.reviewSurface.capitalized) · \(review.approvalMode.replacingOccurrences(of: "_", with: " "))")
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(1)
                                                if !review.sandboxJobId.isEmpty {
                                                    Text("Sandbox lane available")
                                                        .font(.caption2)
                                                        .foregroundStyle(.secondary)
                                                }
                                                HStack(spacing: 8) {
                                                    Button("Approve") {
                                                        Task { await approveStewardshipReview(review) }
                                                    }
                                                    .disabled(governanceActionInFlight != nil)
                                                    .buttonStyle(.plain)
                                                    .padding(.horizontal, 8)
                                                    .padding(.vertical, 4)
                                                    .background(Color.green.opacity(0.16), in: Capsule())
                                                    .font(.caption2.weight(.semibold))

                                                    Button(review.reviewSurface == "home" ? "Route to Brief" : "Route to Home") {
                                                        Task { await routeStewardshipReview(review) }
                                                    }
                                                    .disabled(governanceActionInFlight != nil)
                                                    .buttonStyle(.plain)
                                                    .padding(.horizontal, 8)
                                                    .padding(.vertical, 4)
                                                    .background(Color.blue.opacity(0.16), in: Capsule())
                                                    .font(.caption2.weight(.semibold))

                                                    if !review.sandboxJobId.isEmpty {
                                                        Button("Sandbox") {
                                                            Task { await executeStewardshipReviewSandbox(review) }
                                                        }
                                                        .disabled(governanceActionInFlight != nil)
                                                        .buttonStyle(.plain)
                                                        .padding(.horizontal, 8)
                                                        .padding(.vertical, 4)
                                                        .background(Color.orange.opacity(0.16), in: Capsule())
                                                        .font(.caption2.weight(.semibold))
                                                    }

                                                    Button("Retire") {
                                                        Task { await retireStewardshipReview(review) }
                                                    }
                                                    .disabled(governanceActionInFlight != nil)
                                                    .buttonStyle(.plain)
                                                    .padding(.horizontal, 8)
                                                    .padding(.vertical, 4)
                                                    .background(Color.red.opacity(0.16), in: Capsule())
                                                    .font(.caption2.weight(.semibold))
                                                }
                                            }
                                        }
                                    }
                                }
                                if !adminSummary.governedWorkflows.recentCalendarRoutes.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Calendar Route Lanes")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.governedWorkflows.recentCalendarRoutes.prefix(2)) { route in
                                            let normalizedStatus = route.status.replacingOccurrences(of: "_", with: "-").lowercased()
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(route.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: route.status.replacingOccurrences(of: "_", with: " ").capitalized)
                                                }
                                                Text(route.summary.isEmpty ? route.location : route.summary)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(2)
                                                Text("\(route.location) · \(route.reviewLevel.replacingOccurrences(of: "_", with: " "))")
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(1)
                                                if !route.sandboxJobId.isEmpty {
                                                    Text("Sandbox lane available")
                                                        .font(.caption2)
                                                        .foregroundStyle(.secondary)
                                                }
                                                HStack(spacing: 8) {
                                                    if !route.sandboxJobId.isEmpty && (normalizedStatus.contains("queued") || normalizedStatus.contains("running") || normalizedStatus.contains("stop-requested")) {
                                                        Button("Cancel") {
                                                            Task { await cancelCalendarRouteSandbox(route) }
                                                        }
                                                        .disabled(governanceActionInFlight != nil)
                                                        .buttonStyle(.plain)
                                                        .padding(.horizontal, 8)
                                                        .padding(.vertical, 4)
                                                        .background(Color.red.opacity(0.16), in: Capsule())
                                                        .font(.caption2.weight(.semibold))
                                                    } else if !route.sandboxJobId.isEmpty && (normalizedStatus.contains("sandboxed") || normalizedStatus.contains("failed") || normalizedStatus.contains("cancelled")) {
                                                        Button("Reset") {
                                                            Task { await recoverCalendarRouteSandbox(route) }
                                                        }
                                                        .disabled(governanceActionInFlight != nil)
                                                        .buttonStyle(.plain)
                                                        .padding(.horizontal, 8)
                                                        .padding(.vertical, 4)
                                                        .background(Color.blue.opacity(0.16), in: Capsule())
                                                        .font(.caption2.weight(.semibold))
                                                    } else if !route.sandboxJobId.isEmpty {
                                                        Button("Sandbox") {
                                                            Task { await executeCalendarRouteSandbox(route) }
                                                        }
                                                        .disabled(governanceActionInFlight != nil)
                                                        .buttonStyle(.plain)
                                                        .padding(.horizontal, 8)
                                                        .padding(.vertical, 4)
                                                        .background(Color.orange.opacity(0.16), in: Capsule())
                                                        .font(.caption2.weight(.semibold))
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                                if !adminSummary.governedWorkflows.recentActions.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Recent Action Audit")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.governedWorkflows.recentActions.prefix(2)) { action in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text("\(action.domain.capitalized) · \(action.action)")
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: action.succeeded ? "Succeeded" : "Needs review")
                                                }
                                                Text(action.whyNow.isEmpty ? action.decision : action.whyNow)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(2)
                                                if action.causedFriction {
                                                    Text("Friction observed")
                                                        .font(.caption2.weight(.semibold))
                                                        .foregroundStyle(.orange)
                                                }
                                            }
                                        }
                                    }
                                }
                                if !adminSummary.governedWorkflows.governanceProposals.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Governance Proposals")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.governedWorkflows.governanceProposals.prefix(2)) { proposal in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(proposal.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: proposal.status.capitalized)
                                                }
                                                Text(proposal.promotionReason.isEmpty ? proposal.summary : proposal.promotionReason)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(3)
                                                HStack(spacing: 8) {
                                                    Button("Promote") {
                                                        Task { await promoteGovernanceProposal(proposal) }
                                                    }
                                                    .disabled(governanceActionInFlight != nil)
                                                    .buttonStyle(.plain)
                                                    .padding(.horizontal, 8)
                                                    .padding(.vertical, 4)
                                                    .background(Color.green.opacity(0.16), in: Capsule())
                                                    .font(.caption2.weight(.semibold))

                                                    Button("Dismiss") {
                                                        Task { await dismissGovernanceProposal(proposal) }
                                                    }
                                                    .disabled(governanceActionInFlight != nil)
                                                    .buttonStyle(.plain)
                                                    .padding(.horizontal, 8)
                                                    .padding(.vertical, 4)
                                                    .background(Color.red.opacity(0.16), in: Capsule())
                                                    .font(.caption2.weight(.semibold))
                                                }
                                            }
                                        }
                                    }
                                }
                                if !adminSummary.governedWorkflows.doctrineCandidates.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Doctrine Candidates")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(adminSummary.governedWorkflows.doctrineCandidates.prefix(2)) { candidate in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(candidate.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: candidate.status.capitalized)
                                                }
                                                Text(candidate.promotionReason.isEmpty ? candidate.summary : candidate.promotionReason)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(2)
                                            }
                                        }
                                    }
                                }
                            } else {
                                VStack(alignment: .leading, spacing: 6) {
                                    Text("Admin settings summary not loaded yet.")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                    Text("Fetch state: \(adminSummaryDiagnostics)")
                                        .font(.caption2.monospaced())
                                        .foregroundStyle(.secondary)
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                            }
                        }

                        // ── Sync health ─────────────────────────────
                        SystemsSection(title: "Sync", icon: "arrow.triangle.2.circlepath", accent: steel) {
                            SysRow(label: "Notifications") {
                                syncStatusChip(label: notificationStatusLabel(notificationAuthorizationStatus))
                            }
                            SysRow(label: "Remote Push") {
                                syncStatusChip(label: remoteNotificationsRegistered ? "Registered" : "Not Registered")
                            }
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
                                Task { await refreshNotificationPermissions() }
                            } label: {
                                Label(notificationActionLabel, systemImage: notificationActionSystemImage)
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.bordered)

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

                        SystemsSection(title: "Focus Workflow", icon: "moon.zzz.fill", accent: .indigo) {
                            if let focusState {
                                SysRow(label: "State") {
                                    syncStatusChip(label: focusState.focusActive ? "Active" : "Inactive")
                                }
                                SysRow(label: "Source") {
                                    Text(nonEmpty(focusState.source, fallback: "Unknown"))
                                        .foregroundStyle(.white)
                                }
                                SysRow(label: "Updated") {
                                    Text(nonEmpty(focusState.updatedAt, fallback: nil))
                                        .foregroundStyle(.white)
                                }
                                SysRow(label: "Fresh") {
                                    syncStatusChip(label: focusState.sourceFresh ? "Fresh" : "Stale")
                                }
                                Divider().opacity(0.3)
                                SysRow(label: "Posture") {
                                    syncStatusChip(label: focusState.interruptionPosture.label)
                                }
                                SysRow(label: "Mode") {
                                    Text(readableFocusMode(focusState.filter.jarvisMode))
                                        .foregroundStyle(.white)
                                }
                                SysRow(label: "Delivery") {
                                    Text(readableDeliveryMode(focusState.interruptionPosture.recommendedDelivery))
                                        .foregroundStyle(.white)
                                }
                                SysRow(label: "Local Hour") {
                                    Text("\(focusState.interruptionPosture.hourLocal)")
                                        .foregroundStyle(.white)
                                }
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("Current Controls")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    HStack(spacing: 8) {
                                        pill(
                                            focusState.filter.holdApprovals ? "Approvals Held" : "Approvals Live",
                                            color: focusState.filter.holdApprovals ? .orange.opacity(0.75) : .green.opacity(0.75)
                                        )
                                        pill(
                                            focusState.filter.silenceBriefings ? "Briefings Quiet" : "Briefings Live",
                                            color: focusState.filter.silenceBriefings ? .blue.opacity(0.75) : .green.opacity(0.75)
                                        )
                                    }
                                }
                                if !focusState.summary.detail.isEmpty {
                                    Text(focusState.summary.detail)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                if !focusWorkflowMessage.isEmpty {
                                    Text(focusWorkflowMessage)
                                        .font(.caption2)
                                        .foregroundStyle(.green.opacity(0.86))
                                }
                                if !focusWorkflowError.isEmpty {
                                    Text(focusWorkflowError)
                                        .font(.caption2)
                                        .foregroundStyle(.red.opacity(0.88))
                                }
                                if !focusState.suppressionRules.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Suppression Rules")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(focusState.suppressionRules.prefix(4)) { rule in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(rule.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: rule.active ? "Active" : "Idle")
                                                }
                                                Text(rule.detail)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                            }
                                        }
                                    }
                                }
                                if !focusState.routingLanes.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Routing Lanes")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(focusState.routingLanes) { lane in
                                            VStack(alignment: .leading, spacing: 4) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(lane.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: readableDeliveryMode(lane.deliveryMode))
                                                }
                                                Text(lane.detail)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                if lane.active {
                                                    Text("Active")
                                                        .font(.caption2.weight(.semibold))
                                                        .foregroundStyle(.mint.opacity(0.84))
                                                }
                                            }
                                        }
                                    }
                                }
                                if !focusState.presets.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Apply Preset")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 10) {
                                        ForEach(focusState.presets) { preset in
                                            Button {
                                                Task { await applyFocusPreset(preset) }
                                            } label: {
                                                HStack(alignment: .top, spacing: 12) {
                                                    VStack(alignment: .leading, spacing: 4) {
                                                        HStack(spacing: 8) {
                                                            Text(preset.title)
                                                                .font(.caption.weight(.semibold))
                                                                .foregroundStyle(.white)
                                                            if preset.active {
                                                                pill("Current", color: .green.opacity(0.82))
                                                            }
                                                        }
                                                        Text(preset.detail)
                                                            .font(.caption2)
                                                            .foregroundStyle(.secondary)
                                                        Text("\(readableFocusMode(preset.jarvisMode)) · \(preset.holdApprovals ? "Hold approvals" : "Live approvals") · \(preset.silenceBriefings ? "Quiet briefings" : "Live briefings")")
                                                            .font(.caption2)
                                                            .foregroundStyle(.secondary.opacity(0.9))
                                                    }
                                                    Spacer()
                                                    if focusPresetInFlight == preset.id {
                                                        ProgressView()
                                                            .tint(.white)
                                                    } else {
                                                        Image(systemName: preset.active ? "checkmark.circle.fill" : "arrow.up.forward.circle")
                                                            .foregroundStyle(preset.active ? .green : steel)
                                                    }
                                                }
                                                .padding(12)
                                                .background(Color.white.opacity(preset.active ? 0.08 : 0.05), in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                                            }
                                            .buttonStyle(.plain)
                                            .disabled(focusPresetInFlight != nil)
                                        }
                                    }
                                }
                            } else {
                                Text("Focus workflow not loaded yet.")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }

                        SystemsSection(title: "Signal History", icon: "waveform.badge.magnifyingglass", accent: .mint) {
                            SysRow(label: "Sound Events") {
                                Text("\(soundHistory?.count ?? 0)")
                                    .foregroundStyle(.white)
                            }
                            SysRow(label: "Vision Captures") {
                                Text("\(visionHistory?.count ?? 0)")
                                    .foregroundStyle(.white)
                            }
                            if !signalWorkflowError.isEmpty {
                                Text(signalWorkflowError)
                                    .font(.caption)
                                    .foregroundStyle(.red.opacity(0.9))
                            } else if !signalWorkflowMessage.isEmpty {
                                Text(signalWorkflowMessage)
                                    .font(.caption)
                                    .foregroundStyle(.mint.opacity(0.9))
                            }

                            if let soundHistory, !soundHistory.attentionFlags.isEmpty {
                                Divider().opacity(0.3)
                                Text("Sound Attention")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                VStack(alignment: .leading, spacing: 8) {
                                    ForEach(soundHistory.attentionFlags.prefix(2)) { flag in
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

                            if let soundHistory, !soundHistory.policyRules.isEmpty {
                                Divider().opacity(0.3)
                                Text("Sound Policy")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                VStack(alignment: .leading, spacing: 8) {
                                    ForEach(soundHistory.policyRules) { rule in
                                        VStack(alignment: .leading, spacing: 4) {
                                            HStack(alignment: .firstTextBaseline) {
                                                Text(rule.title)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                Spacer()
                                                syncStatusChip(label: readableDeliveryMode(rule.deliveryMode))
                                            }
                                            Text(rule.detail)
                                                .font(.caption2)
                                                .foregroundStyle(.secondary)
                                            if rule.active {
                                                Text("Active policy")
                                                    .font(.caption2.weight(.semibold))
                                                    .foregroundStyle(.mint.opacity(0.84))
                                            }
                                        }
                                    }
                                }
                            }

                            if let soundHistory, !soundHistory.responsePlans.isEmpty {
                                Divider().opacity(0.3)
                                Text("Sound Follow-up")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                VStack(alignment: .leading, spacing: 8) {
                                    ForEach(soundHistory.responsePlans) { plan in
                                        VStack(alignment: .leading, spacing: 4) {
                                            HStack(alignment: .firstTextBaseline) {
                                                Text(plan.title)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                Spacer()
                                                syncStatusChip(label: plan.priority.capitalized)
                                            }
                                            Text(plan.detail)
                                                .font(.caption2)
                                                .foregroundStyle(.secondary)
                                            Text("Target: \(plan.target.capitalized)")
                                                .font(.caption2)
                                                .foregroundStyle(plan.active ? .mint.opacity(0.84) : .secondary)
                                        }
                                    }
                                }
                            }

                            if let soundHistory, !soundHistory.recentItems.isEmpty {
                                Divider().opacity(0.3)
                                Text("Recent Sound")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                VStack(alignment: .leading, spacing: 8) {
                                    ForEach(soundHistory.recentItems.prefix(3)) { item in
                                        VStack(alignment: .leading, spacing: 3) {
                                            HStack(alignment: .firstTextBaseline) {
                                                Text(item.label.isEmpty ? "Sound alert" : item.label)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                Spacer()
                                                if let confidence = item.confidence {
                                                    Text("\(Int(confidence * 100))%")
                                                        .font(.caption2)
                                                        .foregroundStyle(.secondary)
                                                }
                                            }
                                            if !item.detail.isEmpty {
                                                Text(item.detail)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                            }
                                            if item.resolved {
                                                Text("Resolved \(nonEmpty(item.resolvedAt, fallback: nil))")
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                            } else {
                                                Button {
                                                    Task { await resolveSoundItem(item) }
                                                } label: {
                                                    Label("Resolve", systemImage: "checkmark.circle")
                                                        .font(.caption2.weight(.semibold))
                                                        .foregroundStyle(.mint)
                                                }
                                                .buttonStyle(.plain)
                                            }
                                            Text(nonEmpty(item.receivedAt, fallback: nil))
                                                .font(.caption2)
                                                .foregroundStyle(.secondary)
                                        }
                                    }
                                }
                            }

                            if let visionHistory, !visionHistory.recentItems.isEmpty {
                                if !visionHistory.policyRules.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Vision Policy")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(visionHistory.policyRules) { rule in
                                            VStack(alignment: .leading, spacing: 4) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(rule.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: readableDeliveryMode(rule.deliveryMode))
                                                }
                                                Text(rule.detail)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                if rule.active {
                                                    Text("Active policy")
                                                        .font(.caption2.weight(.semibold))
                                                        .foregroundStyle(.mint.opacity(0.84))
                                                }
                                            }
                                        }
                                    }
                                }

                                if !visionHistory.responsePlans.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Vision Follow-up")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(visionHistory.responsePlans) { plan in
                                            VStack(alignment: .leading, spacing: 4) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(plan.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: plan.priority.capitalized)
                                                }
                                                Text(plan.detail)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                Text("Target: \(plan.target.capitalized)")
                                                    .font(.caption2)
                                                    .foregroundStyle(plan.active ? .mint.opacity(0.84) : .secondary)
                                            }
                                        }
                                    }
                                }

                                Divider().opacity(0.3)
                                Text("Recent Vision")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                VStack(alignment: .leading, spacing: 8) {
                                    ForEach(visionHistory.recentItems.prefix(3)) { item in
                                        VStack(alignment: .leading, spacing: 3) {
                                            HStack(alignment: .firstTextBaseline) {
                                                Text(item.context.isEmpty ? "Vision scan" : item.context)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                Spacer()
                                                if !item.source.isEmpty {
                                                    syncStatusChip(label: item.source.capitalized)
                                                }
                                            }
                                            if !item.textPreview.isEmpty {
                                                Text(item.textPreview)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(3)
                                            }
                                            if item.resolved {
                                                Text("Resolved \(nonEmpty(item.resolvedAt, fallback: nil))")
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                            } else {
                                                Button {
                                                    Task { await resolveVisionItem(item) }
                                                } label: {
                                                    Label("Resolve", systemImage: "checkmark.circle")
                                                        .font(.caption2.weight(.semibold))
                                                        .foregroundStyle(.mint)
                                                }
                                                .buttonStyle(.plain)
                                            }
                                            Text(nonEmpty(item.receivedAt, fallback: nil))
                                                .font(.caption2)
                                                .foregroundStyle(.secondary)
                                        }
                                    }
                                }
                            }
                        }

                        SystemsSection(title: "Media Workflow", icon: "music.note.tv.fill", accent: .purple) {
                            if let nowPlayingState {
                                SysRow(label: "State") {
                                    syncStatusChip(label: nowPlayingState.isPlaying ? "Playing" : "Idle")
                                }
                                SysRow(label: "Updated") {
                                    Text(nonEmpty(nowPlayingState.updatedAt, fallback: nil))
                                        .foregroundStyle(.white)
                                }
                                SysRow(label: "Artwork") {
                                    syncStatusChip(label: nowPlayingState.artworkAvailable ? "Available" : "Missing")
                                }
                                if !nowPlayingState.title.isEmpty {
                                    Text("\(nowPlayingState.title)\(nowPlayingState.artist.isEmpty ? "" : " · \(nowPlayingState.artist)")")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                        .lineLimit(2)
                                }
                                Divider().opacity(0.3)
                                Text("Ambient Media Posture")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                Text(nowPlayingState.summary.label)
                                    .font(.caption.bold())
                                    .foregroundStyle(.white)
                                Text(nowPlayingState.summary.detail)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                                if !nowPlayingState.routingRules.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Routing Rules")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(nowPlayingState.routingRules.prefix(3)) { rule in
                                            VStack(alignment: .leading, spacing: 4) {
                                                HStack(alignment: .top) {
                                                    Text(rule.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: readableDeliveryMode(rule.deliveryMode))
                                                }
                                                Text(rule.detail)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                if rule.active {
                                                    Text("Active now")
                                                        .font(.caption2.weight(.semibold))
                                                        .foregroundStyle(.mint)
                                                }
                                            }
                                        }
                                    }
                                }
                                if !nowPlayingState.responsePlans.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Session Plans")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(nowPlayingState.responsePlans.prefix(3)) { plan in
                                            VStack(alignment: .leading, spacing: 4) {
                                                HStack(alignment: .top) {
                                                    Text(plan.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: plan.priority.capitalized)
                                                }
                                                Text(plan.detail)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                Text(plan.target.capitalized)
                                                    .font(.caption2.weight(.semibold))
                                                    .foregroundStyle(plan.active ? .mint : .secondary)
                                            }
                                        }
                                    }
                                }
                                if !nowPlayingState.suggestedControls.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Recommended Controls")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(nowPlayingState.suggestedControls.prefix(3)) { control in
                                            VStack(alignment: .leading, spacing: 4) {
                                                HStack(alignment: .top) {
                                                    Text(control.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: control.style.capitalized)
                                                }
                                                Text(control.detail)
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                                if control.active {
                                                    Text("Ready")
                                                        .font(.caption2.weight(.semibold))
                                                        .foregroundStyle(.mint)
                                                }
                                            }
                                        }
                                    }
                                }
                                if !nowPlayingState.recentItems.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Recent Media Events")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(nowPlayingState.recentItems.prefix(3)) { item in
                                            VStack(alignment: .leading, spacing: 3) {
                                                Text(item.title.isEmpty ? "Media update" : item.title)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                if !item.detail.isEmpty {
                                                    Text(item.detail)
                                                        .font(.caption2)
                                                        .foregroundStyle(.secondary)
                                                }
                                                Text(nonEmpty(item.ts, fallback: nil))
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                            }
                                        }
                                    }
                                }
                            } else {
                                Text("Now playing workflow not loaded yet.")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }

                        SystemsSection(title: "Control Plane", icon: "switch.2", accent: steel) {
                            if let controlPlane {
                                SysRow(label: "Notifications") {
                                    Text("\(controlPlane.notifications.total) total · \(controlPlane.notifications.pending) pending")
                                        .foregroundStyle(.white)
                                }
                                SysRow(label: "Event Spine") {
                                    Text("\(controlPlane.events.recentCount) recent")
                                        .foregroundStyle(.white)
                                }
                                SysRow(label: "Last Event") {
                                    Text(nonEmpty(controlPlane.events.lastEventAt, fallback: nil))
                                        .foregroundStyle(.white)
                                }
                                SysRow(label: "Notif Freshness") {
                                    Text(nonEmpty(controlPlane.notifications.lastUpdatedAt, fallback: nil))
                                        .foregroundStyle(.white)
                                }
                                Divider().opacity(0.3)
                                Text("Notification Status")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                HStack(spacing: 10) {
                                    systemsMetric("Seen", "\(controlPlane.notifications.seen)")
                                    systemsMetric("Snoozed", "\(controlPlane.notifications.snoozed)")
                                    systemsMetric("Resolved", "\(controlPlane.notifications.resolved)")
                                }
                                Divider().opacity(0.3)
                                Text("Event Domains")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                VStack(alignment: .leading, spacing: 6) {
                                    ForEach(controlPlane.events.domains.keys.sorted().prefix(4), id: \.self) { key in
                                        SysRow(label: key.capitalized) {
                                            Text("\(controlPlane.events.domains[key] ?? 0)")
                                                .foregroundStyle(.white)
                                        }
                                    }
                                }
                                if !controlPlane.freshness.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Source Freshness")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(controlPlane.freshness.prefix(8)) { item in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(item.label)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    syncStatusChip(label: readableFreshnessStatus(item.status))
                                                }
                                                if !item.detail.isEmpty {
                                                    Text(item.detail)
                                                        .font(.caption2)
                                                        .foregroundStyle(.secondary)
                                                }
                                                Text(nonEmpty(item.updatedAt, fallback: "Not updated yet"))
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                            }
                                        }
                                    }
                                }
                                if !controlPlane.events.recentItems.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Recent Event Flow")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(controlPlane.events.recentItems.prefix(4)) { item in
                                            VStack(alignment: .leading, spacing: 3) {
                                                HStack(alignment: .firstTextBaseline) {
                                                    Text(item.title.isEmpty ? "Event" : item.title)
                                                        .font(.caption.bold())
                                                        .foregroundStyle(.white)
                                                    Spacer()
                                                    if !item.domain.isEmpty {
                                                        syncStatusChip(label: item.domain.capitalized)
                                                    }
                                                }
                                                if !item.detail.isEmpty {
                                                    Text(item.detail)
                                                        .font(.caption2)
                                                        .foregroundStyle(.secondary)
                                                }
                                                HStack(spacing: 8) {
                                                    if !item.severity.isEmpty {
                                                        Text(item.severity.capitalized)
                                                            .font(.caption2)
                                                            .foregroundStyle(.secondary)
                                                    }
                                                    Text(nonEmpty(item.ts, fallback: nil))
                                                        .font(.caption2)
                                                        .foregroundStyle(.secondary)
                                                }
                                            }
                                        }
                                    }
                                }
                            } else {
                                Text("Control plane summary not loaded yet.")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
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
                                HStack(spacing: 10) {
                                    calendarSummaryMetric(title: "Today", value: "\(calendarState.todayEvents.count)")
                                    calendarSummaryMetric(title: "Route", value: "\(calendarState.routeSensitiveEvents.count)")
                                    calendarSummaryMetric(title: "Prep", value: "\(calendarState.preparationCues.count)")
                                }
                                .padding(.vertical, 4)

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
                                            calendarWorkflowEventCard(event)
                                        }
                                    }
                                }

                                if !calendarState.todayEvents.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Today")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 10) {
                                        ForEach(calendarState.todayEvents.prefix(3)) { event in
                                            calendarWorkflowEventCard(event)
                                        }
                                    }
                                }

                                if !calendarState.routeSensitiveEvents.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Route Window")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 10) {
                                        ForEach(calendarState.routeSensitiveEvents.prefix(3)) { event in
                                            calendarWorkflowEventCard(event)
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
                                                if let event = calendarEvent(for: cue.eventId) {
                                                    HStack(spacing: 10) {
                                                        Button("Stage Prep") {
                                                            Task { await prepareCalendarEvent(event) }
                                                        }
                                                        .buttonStyle(.borderedProminent)
                                                        .tint(.cyan)

                                                        if event.routeReady {
                                                            Button("Route") {
                                                                Task { await routeCalendarEvent(event) }
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
                                HStack(spacing: 10) {
                                    reminderSummaryMetric(title: "Overdue", value: "\(remindersState.summary.overdueCount)")
                                    reminderSummaryMetric(title: "Due Soon", value: "\(remindersState.summary.dueSoonCount)")
                                    reminderSummaryMetric(title: "Priority", value: "\(remindersState.summary.priorityCount)")
                                    reminderSummaryMetric(title: "No Due", value: "\(remindersState.summary.noDueDateCount)")
                                }
                                .padding(.vertical, 4)

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

                                if !remindersState.listSummaries.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Lists")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    VStack(alignment: .leading, spacing: 8) {
                                        ForEach(remindersState.listSummaries.prefix(4)) { summary in
                                            HStack(alignment: .firstTextBaseline) {
                                                Text(summary.title)
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                                Spacer()
                                                Text("\(summary.count)")
                                                    .font(.caption.bold())
                                                    .foregroundStyle(.white)
                                            }
                                            HStack(spacing: 8) {
                                                if summary.overdueCount > 0 {
                                                    syncStatusChip(label: "\(summary.overdueCount) overdue")
                                                }
                                                if summary.dueSoonCount > 0 {
                                                    syncStatusChip(label: "\(summary.dueSoonCount) due soon")
                                                }
                                                if summary.priorityCount > 0 {
                                                    syncStatusChip(label: "\(summary.priorityCount) priority")
                                                }
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
                                }
                                if !remindersState.dueSoonItems.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Due Soon")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    reminderWorkflowList(remindersState.dueSoonItems.prefix(3))
                                }
                                if !remindersState.priorityItems.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Priority")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    reminderWorkflowList(remindersState.priorityItems.prefix(3))
                                }
                                if !remindersState.openItems.isEmpty {
                                    Divider().opacity(0.3)
                                    Text("Open Queue")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    reminderWorkflowList(remindersState.openItems.prefix(4))
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

                            Button {
                                handleLocationAccessAction()
                            } label: {
                                Label(locationActionLabel, systemImage: locationActionSystemImage)
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.bordered)
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

    @MainActor
    private func refreshSystems() async {
        let startedAt = Date()
        refreshGeneration += 1
        let generation = refreshGeneration
        print("[JARVIS Systems] refresh \(generation) started")
        isRefreshing = true
        defer {
            if generation == refreshGeneration {
                isRefreshing = false
            }
            print("[JARVIS Systems] refresh \(generation) finished in \(String(format: "%.3f", Date().timeIntervalSince(startedAt)))s")
        }
        let notificationStatusTask = Task {
            await refreshNotificationStatus()
        }
        async let watchStatusRequest = AppleAPIClient.shared.fetchStatus()
        async let appStateRequest = AppleAPIClient.shared.fetchAppState()
        let controlPlaneTask = Task {
            try await AppleAPIClient.shared.fetchControlPlaneState()
        }
        adminSummaryDiagnostics = "Request queued at \(Date().formatted(date: .omitted, time: .standard))"
        let adminSummaryTask = Task {
            try await AppleAPIClient.shared.fetchSystemsAdminSummary()
        }

        Task {
            do {
                let result = try await adminSummaryTask.value
                await MainActor.run {
                    guard generation == refreshGeneration else { return }
                    adminSummary = result
                    adminSummaryDiagnostics = "Loaded in \(String(format: "%.3f", Date().timeIntervalSince(startedAt)))s"
                    print("[JARVIS Systems] refresh \(generation) promoted adminSummary in \(String(format: "%.3f", Date().timeIntervalSince(startedAt)))s")
                }
            } catch {
                await MainActor.run {
                    guard generation == refreshGeneration else { return }
                    adminSummary = nil
                    adminSummaryDiagnostics = "Failed after \(String(format: "%.3f", Date().timeIntervalSince(startedAt)))s: \(error.localizedDescription)"
                    print("[JARVIS Systems] refresh \(generation) adminSummary failed after \(String(format: "%.3f", Date().timeIntervalSince(startedAt)))s error=\(error.localizedDescription)")
                }
            }
        }

        Task {
            let result = try? await controlPlaneTask.value
            await MainActor.run {
                guard generation == refreshGeneration else { return }
                controlPlane = result
            }
        }

        var essentialIssues: [String] = []

        do {
            watchStatus = try await watchStatusRequest
        } catch {
            watchStatus = nil
            essentialIssues.append("Status: \(error.localizedDescription)")
        }

        do {
            appState = try await appStateRequest
        } catch {
            appState = nil
            essentialIssues.append("App State: \(error.localizedDescription)")
        }

        serverOK = essentialIssues.isEmpty
        pingError = essentialIssues.isEmpty ? nil : essentialIssues.joined(separator: "  ")
        if serverOK {
            calendarWorkflowError = ""
            reminderWorkflowError = ""
        }

        await notificationStatusTask.value

        // Promote shared-state truth as soon as the fast critical sections are ready
        // instead of withholding Admin and control-plane data behind slower history loads.
        _ = try? await adminSummaryTask.value
        _ = try? await controlPlaneTask.value

        Task {
            async let calendarStateRequest = AppleAPIClient.shared.fetchCalendarState()
            async let remindersStateRequest = AppleAPIClient.shared.fetchRemindersState()
            async let focusStateRequest = AppleAPIClient.shared.fetchFocusState()
            async let soundHistoryRequest = AppleAPIClient.shared.fetchSoundHistory()
            async let visionHistoryRequest = AppleAPIClient.shared.fetchVisionHistory()
            async let nowPlayingStateRequest = AppleAPIClient.shared.fetchNowPlayingState()

            let calendar = try? await calendarStateRequest
            let reminders = try? await remindersStateRequest
            let focus = try? await focusStateRequest
            let sound = try? await soundHistoryRequest
            let vision = try? await visionHistoryRequest
            let nowPlaying = try? await nowPlayingStateRequest

            await MainActor.run {
                guard generation == refreshGeneration else { return }
                calendarState = calendar
                remindersState = reminders
                focusState = focus
                soundHistory = sound
                visionHistory = vision
                nowPlayingState = nowPlaying
                print("[JARVIS Systems] refresh \(generation) deferred slices promoted in \(String(format: "%.3f", Date().timeIntervalSince(startedAt)))s")
            }
        }
    }

    @MainActor
    private func refreshNotificationPermissions() async {
        await refreshNotificationStatus()

        switch notificationAuthorizationStatus {
        case .notDetermined:
            (UIApplication.shared.delegate as? AppDelegate)?.requestNotificationPermissionIfNeeded()
            try? await Task.sleep(for: .milliseconds(500))
            await refreshNotificationStatus()
        case .authorized, .provisional, .ephemeral:
            UIApplication.shared.registerForRemoteNotifications()
            try? await Task.sleep(for: .milliseconds(250))
            await refreshNotificationStatus()
        case .denied:
            if let settingsURL = URL(string: UIApplication.openSettingsURLString) {
                openURL(settingsURL)
            }
        @unknown default:
            break
        }
    }

    @MainActor
    private func refreshNotificationStatus() async {
        let settings = await UNUserNotificationCenter.current().notificationSettings()
        notificationAuthorizationStatus = settings.authorizationStatus
        remoteNotificationsRegistered = UIApplication.shared.isRegisteredForRemoteNotifications
    }

    private func applyFocusPreset(_ preset: FocusPreset) async {
        focusPresetInFlight = preset.id
        focusWorkflowMessage = ""
        focusWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.applyFocusPreset(
                focusActive: preset.focusActive,
                jarvisMode: preset.jarvisMode,
                holdApprovals: preset.holdApprovals,
                silenceBriefings: preset.silenceBriefings
            )
            switch result.status {
            case "stored":
                focusWorkflowMessage = "\(preset.title) applied."
            case "staged_for_review":
                focusWorkflowError = result.boundaryReason ?? "\(preset.title) was staged for review."
            case "blocked_by_boundary":
                focusWorkflowError = result.boundaryReason ?? "\(preset.title) was blocked by governance boundaries."
            default:
                focusWorkflowMessage = "\(preset.title) updated."
            }
            await refreshSystems()
        } catch {
            focusWorkflowError = error.localizedDescription
        }
        focusPresetInFlight = nil
    }

    private func promoteTrustZone(_ zone: SystemsAdminGovernanceZone) async {
        governanceActionInFlight = "zone-promote-\(zone.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.promoteTrustZone(zone.id)
            governanceWorkflowMessage = "\(zone.name.isEmpty ? zone.id : zone.name) promoted to \(result.authorityStage.replacingOccurrences(of: "_", with: " ").capitalized)."
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func demoteTrustZone(_ zone: SystemsAdminGovernanceZone) async {
        governanceActionInFlight = "zone-demote-\(zone.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.demoteTrustZone(zone.id)
            governanceWorkflowMessage = "\(zone.name.isEmpty ? zone.id : zone.name) moved back to \(result.authorityStage.replacingOccurrences(of: "_", with: " ").capitalized)."
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func suspendResourceArena(_ arena: SystemsAdminGovernanceArena) async {
        governanceActionInFlight = "arena-suspend-\(arena.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.suspendResourceArena(arena.id)
            governanceWorkflowMessage = "\(arena.name.isEmpty ? arena.id : arena.name) is now \(result.status)."
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func resumeResourceArena(_ arena: SystemsAdminGovernanceArena) async {
        governanceActionInFlight = "arena-resume-\(arena.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.resumeResourceArena(arena.id)
            governanceWorkflowMessage = "\(arena.name.isEmpty ? arena.id : arena.name) is now \(result.status)."
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func executeSandboxJob(_ job: SystemsAdminSandboxJob) async {
        governanceActionInFlight = "sandbox-\(job.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.executeSandboxJob(job.id)
            governanceWorkflowMessage = result.accepted
                ? "\(job.title.isEmpty ? job.id : job.title) entered the sandbox queue."
                : result.message
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func cancelSandboxJob(_ job: SystemsAdminSandboxJob) async {
        governanceActionInFlight = "sandbox-cancel-\(job.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.cancelSandboxJob(job.id)
            governanceWorkflowMessage = result.mode == "stop-requested"
                ? "\(job.title.isEmpty ? job.id : job.title) will stop at the next safe sandbox checkpoint."
                : (result.message.isEmpty ? "\(job.title.isEmpty ? job.id : job.title) was cancelled." : result.message)
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func recoverSandboxJob(_ job: SystemsAdminSandboxJob) async {
        governanceActionInFlight = "sandbox-recover-\(job.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.recoverSandboxJob(job.id)
            governanceWorkflowMessage = result.message.isEmpty
                ? "\(job.title.isEmpty ? job.id : job.title) returned to sandbox baseline."
                : result.message
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func approveStewardshipReview(_ review: SystemsAdminStewardshipReviewItem) async {
        governanceActionInFlight = "stewardship-approve-\(review.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.approveStewardshipReview(review.id)
            governanceWorkflowMessage = "\(result.laneTitle) approved for \(result.packetTarget.capitalized)."
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func routeStewardshipReview(_ review: SystemsAdminStewardshipReviewItem) async {
        governanceActionInFlight = "stewardship-route-\(review.id)"
        governanceWorkflowError = ""
        let nextSurface = review.reviewSurface == "home" ? "brief" : "home"
        let nextTarget = nextSurface == "home" ? "family" : "executive"
        do {
            let result = try await AppleAPIClient.shared.routeStewardshipReview(
                review.id,
                reviewSurface: nextSurface,
                packetTarget: nextTarget
            )
            governanceWorkflowMessage = "\(result.laneTitle) rerouted to \(result.reviewSurface.capitalized)."
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func retireStewardshipReview(_ review: SystemsAdminStewardshipReviewItem) async {
        governanceActionInFlight = "stewardship-retire-\(review.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.retireStewardshipReview(
                review.id,
                reason: "\(review.laneTitle) was retired from Systems/Admin."
            )
            governanceWorkflowMessage = result.boundaryReason.isEmpty
                ? "\(result.laneTitle) retired."
                : result.boundaryReason
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func executeStewardshipReviewSandbox(_ review: SystemsAdminStewardshipReviewItem) async {
        guard !review.sandboxJobId.isEmpty else { return }
        governanceActionInFlight = "stewardship-sandbox-\(review.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.executeSandboxJob(
                review.sandboxJobId,
                triggeredBy: "apple-stewardship-review"
            )
            governanceWorkflowMessage = result.message.isEmpty
                ? "\(review.laneTitle) entered the bounded sandbox lane."
                : result.message
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func executeCalendarRouteSandbox(_ route: SystemsAdminCalendarRouteItem) async {
        guard !route.sandboxJobId.isEmpty else { return }
        governanceActionInFlight = "calendar-route-sandbox-\(route.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.executeSandboxJob(
                route.sandboxJobId,
                triggeredBy: "apple-calendar-route"
            )
            governanceWorkflowMessage = result.message.isEmpty
                ? "\(route.title) entered the bounded calendar route lane."
                : result.message
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func cancelCalendarRouteSandbox(_ route: SystemsAdminCalendarRouteItem) async {
        guard !route.sandboxJobId.isEmpty else { return }
        governanceActionInFlight = "calendar-route-cancel-\(route.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.cancelSandboxJob(
                route.sandboxJobId,
                reason: "manual stop from calendar route lane"
            )
            governanceWorkflowMessage = result.message.isEmpty
                ? "\(route.title) left the bounded calendar route lane."
                : result.message
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func recoverCalendarRouteSandbox(_ route: SystemsAdminCalendarRouteItem) async {
        guard !route.sandboxJobId.isEmpty else { return }
        governanceActionInFlight = "calendar-route-recover-\(route.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.recoverSandboxJob(
                route.sandboxJobId,
                reason: "manual recovery reset from calendar route lane"
            )
            governanceWorkflowMessage = result.message.isEmpty
                ? "\(route.title) returned to the governed route baseline."
                : result.message
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func promoteGovernanceProposal(_ proposal: SystemsAdminDoctrineCandidateItem) async {
        governanceActionInFlight = "governance-promote-\(proposal.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.promoteGovernanceProposal(
                proposal.id,
                basis: proposal.promotionReason.isEmpty ? "Promoted from Systems/Admin." : proposal.promotionReason
            )
            governanceWorkflowMessage = result.message
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func dismissGovernanceProposal(_ proposal: SystemsAdminDoctrineCandidateItem) async {
        governanceActionInFlight = "governance-dismiss-\(proposal.id)"
        governanceWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.dismissGovernanceProposal(
                proposal.id,
                reason: proposal.promotionReason.isEmpty ? "Dismissed from Systems/Admin." : proposal.promotionReason
            )
            governanceWorkflowMessage = result.message
            await refreshSystems()
        } catch {
            governanceWorkflowError = error.localizedDescription
        }
        governanceActionInFlight = nil
    }

    private func refreshEventSync() async {
        await eventSync.requestAccessAndSync()
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

    private func notificationStatusLabel(_ status: UNAuthorizationStatus) -> String {
        switch status {
        case .authorized:
            return "Allowed"
        case .provisional:
            return "Provisional"
        case .ephemeral:
            return "Ephemeral"
        case .denied:
            return "Blocked"
        case .notDetermined:
            return "Not Asked"
        @unknown default:
            return "Unknown"
        }
    }

    private var notificationActionLabel: String {
        switch notificationAuthorizationStatus {
        case .notDetermined:
            return "Enable Notifications"
        case .authorized, .provisional, .ephemeral:
            return remoteNotificationsRegistered ? "Refresh Notification Registration" : "Register for Push Notifications"
        case .denied:
            return "Open Notification Settings"
        @unknown default:
            return "Review Notification Access"
        }
    }

    private var notificationActionSystemImage: String {
        switch notificationAuthorizationStatus {
        case .denied:
            return "gearshape"
        case .authorized, .provisional, .ephemeral:
            return "bell.badge"
        case .notDetermined:
            return "bell"
        @unknown default:
            return "bell"
        }
    }

    private var locationActionLabel: String {
        switch weatherLocation.authorizationStatus {
        case .notDetermined:
            return "Enable Location Access"
        case .authorizedWhenInUse:
            return "Upgrade Presence to Always"
        case .authorizedAlways:
            return geofence.homeCoordinate == nil ? "Set Home Geofence" : "Refresh Presence Monitoring"
        case .denied, .restricted:
            return "Open Location Settings"
        @unknown default:
            return "Review Location Access"
        }
    }

    private var locationActionSystemImage: String {
        switch weatherLocation.authorizationStatus {
        case .notDetermined:
            return "location"
        case .authorizedWhenInUse:
            return "location.badge.plus"
        case .authorizedAlways:
            return geofence.homeCoordinate == nil ? "house.badge.plus" : "location.circle"
        case .denied, .restricted:
            return "gearshape"
        @unknown default:
            return "location"
        }
    }

    @MainActor
    private func handleLocationAccessAction() {
        switch weatherLocation.authorizationStatus {
        case .notDetermined:
            weatherLocation.requestPermission()
        case .authorizedWhenInUse:
            geofence.requestPermission()
        case .authorizedAlways:
            if geofence.homeCoordinate == nil {
                geofence.setHomeToCurrentLocation()
            } else {
                geofence.startMonitoring()
            }
        case .denied, .restricted:
            if let settingsURL = URL(string: UIApplication.openSettingsURLString) {
                openURL(settingsURL)
            }
        @unknown default:
            break
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

    private func readableFocusMode(_ mode: String) -> String {
        switch mode {
        case "morning_brief":
            return "Morning Brief"
        case "work":
            return "Work Focus"
        case "daily_recap":
            return "Daily Recap"
        case "sleep":
            return "Sleep"
        case "personal":
            return "Personal Time"
        default:
            return mode.replacingOccurrences(of: "_", with: " ").capitalized
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

    private func readableFreshnessStatus(_ status: String) -> String {
        switch status {
        case "fresh":
            return "Fresh"
        case "stale":
            return "Stale"
        case "not_synced":
            return "Not Synced"
        default:
            return status.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }

    private func adminCurrency(_ value: Double) -> String {
        value.formatted(.currency(code: "USD").precision(.fractionLength(2)))
    }

    private func shortTokenCount(_ value: Int) -> String {
        if value >= 1_000_000 {
            return String(format: "%.1fM", Double(value) / 1_000_000)
        }
        if value >= 1_000 {
            return String(format: "%.1fK", Double(value) / 1_000)
        }
        return "\(value)"
    }

    private func resolveSoundItem(_ item: SoundHistoryItem) async {
        signalWorkflowError = ""
        signalWorkflowMessage = ""
        do {
            let result = try await AppleAPIClient.shared.resolveSoundAlert(item.id)
            switch result.status {
            case "resolved":
                signalWorkflowMessage = "Resolved sound alert."
            case "staged_for_review":
                signalWorkflowMessage = result.boundaryReason?.isEmpty == false
                    ? result.boundaryReason!
                    : "Sound alert staged for review."
            case "blocked_by_boundary":
                signalWorkflowError = result.boundaryReason?.isEmpty == false
                    ? result.boundaryReason!
                    : "JARVIS could not resolve that sound alert."
            default:
                signalWorkflowError = "JARVIS could not resolve that sound alert."
            }
            await refreshSystems()
        } catch {
            signalWorkflowError = error.localizedDescription
        }
    }

    private func resolveVisionItem(_ item: VisionHistoryItem) async {
        signalWorkflowError = ""
        signalWorkflowMessage = ""
        do {
            let result = try await AppleAPIClient.shared.resolveVisionScan(item.id)
            switch result.status {
            case "resolved":
                signalWorkflowMessage = "Resolved vision scan."
            case "staged_for_review":
                signalWorkflowMessage = result.boundaryReason?.isEmpty == false
                    ? result.boundaryReason!
                    : "Vision scan staged for review."
            case "blocked_by_boundary":
                signalWorkflowError = result.boundaryReason?.isEmpty == false
                    ? result.boundaryReason!
                    : "JARVIS could not resolve that vision scan."
            default:
                signalWorkflowError = "JARVIS could not resolve that vision scan."
            }
            await refreshSystems()
        } catch {
            signalWorkflowError = error.localizedDescription
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

    private func calendarSummaryMetric(title: String, value: String) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.caption.bold())
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }

    private func routeCalendarEvent(_ event: CalendarWorkflowEvent) async {
        calendarWorkflowError = ""
        do {
            let route = try await AppleAPIClient.shared.routeCalendarEvent(event.id)
            switch route.status {
            case "ready":
                calendarWorkflowMessage = "Route ready for \(route.title)"
            case "staged_for_review":
                calendarWorkflowMessage = route.boundaryReason?.isEmpty == false
                    ? route.boundaryReason!
                    : "Route staged for review: \(route.title)"
            case "blocked_by_boundary":
                calendarWorkflowMessage = route.boundaryReason?.isEmpty == false
                    ? route.boundaryReason!
                    : "Route blocked by boundary for \(route.title)"
            default:
                calendarWorkflowMessage = "Route updated for \(route.title)"
            }
            if route.status == "ready", let url = URL(string: route.mapsURL), !route.mapsURL.isEmpty {
                openURL(url)
            }
            calendarState = try await AppleAPIClient.shared.fetchCalendarState()
        } catch {
            calendarWorkflowError = error.localizedDescription
        }
    }

    private func calendarEvent(for eventId: String) -> CalendarWorkflowEvent? {
        guard let calendarState else { return nil }
        return (calendarState.nextEvents + calendarState.todayEvents + calendarState.routeSensitiveEvents)
            .first { $0.id == eventId }
    }

    @ViewBuilder
    private func calendarWorkflowEventCard(_ event: CalendarWorkflowEvent) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack(alignment: .firstTextBaseline) {
                Text(event.title.isEmpty ? "Upcoming event" : event.title)
                    .font(.caption.bold())
                    .foregroundStyle(.white)
                Spacer()
                if !event.calendar.isEmpty {
                    syncStatusChip(label: event.calendar)
                }
            }
            Text(calendarTimingLabel(for: event))
                .font(.caption2)
                .foregroundStyle(.secondary)
            if !event.location.isEmpty {
                Text(event.location)
                    .font(.caption2)
                    .foregroundStyle(.cyan.opacity(0.8))
            }
            if !event.notes.isEmpty {
                Text(event.notes)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
            HStack(spacing: 10) {
                Button("Stage Prep") {
                    Task { await prepareCalendarEvent(event) }
                }
                .buttonStyle(.borderedProminent)
                .tint(.cyan)

                if event.routeReady {
                    Button("Route") {
                        Task { await routeCalendarEvent(event) }
                    }
                    .buttonStyle(.bordered)
                    .tint(.white.opacity(0.85))
                }

                if !event.url.isEmpty {
                    Button("Open Link") {
                        guard let url = URL(string: event.url) else { return }
                        openURL(url)
                    }
                    .buttonStyle(.bordered)
                    .tint(.white.opacity(0.7))
                }
            }
            .font(.caption.weight(.semibold))
        }
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

    private func reminderSummaryMetric(title: String, value: String) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.caption.bold())
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }

    private func completeReminderWorkflow(_ item: ReminderWorkflowItem) async {
        reminderWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.completeReminder(item.id)
            if result.status == "completed" {
                reminderWorkflowMessage = "Completed \(item.title)"
                remindersState = try await AppleAPIClient.shared.fetchRemindersState()
                appState = try await AppleAPIClient.shared.fetchAppState()
            } else if result.status == "staged_for_review" {
                reminderWorkflowError = result.boundaryReason ?? "Reminder completion was staged for review."
                remindersState = try await AppleAPIClient.shared.fetchRemindersState()
            } else if result.status == "blocked_by_boundary" {
                reminderWorkflowError = result.boundaryReason ?? "Reminder completion was blocked by boundary policy."
                remindersState = try await AppleAPIClient.shared.fetchRemindersState()
            }
        } catch {
            reminderWorkflowError = error.localizedDescription
        }
    }

    private func snoozeReminderWorkflow(_ item: ReminderWorkflowItem) async {
        reminderWorkflowError = ""
        do {
            let result = try await AppleAPIClient.shared.snoozeReminder(item.id, minutes: 60)
            if result.status == "snoozed" {
                reminderWorkflowMessage = "Snoozed \(item.title) for 1 hour"
                remindersState = try await AppleAPIClient.shared.fetchRemindersState()
                appState = try await AppleAPIClient.shared.fetchAppState()
            } else if result.status == "staged_for_review" {
                reminderWorkflowError = result.boundaryReason ?? "Reminder snooze was staged for review."
                remindersState = try await AppleAPIClient.shared.fetchRemindersState()
            } else if result.status == "blocked_by_boundary" {
                reminderWorkflowError = result.boundaryReason ?? "Reminder snooze was blocked by boundary policy."
                remindersState = try await AppleAPIClient.shared.fetchRemindersState()
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

    @State private var overview: NotificationCenterOverview?
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

                                if let routing = overview?.routing {
                                    VStack(alignment: .leading, spacing: 10) {
                                        sectionHeader("Ambient Routing", icon: "point.3.connected.trianglepath.dotted")
                                        HStack(alignment: .top, spacing: 10) {
                                            VStack(alignment: .leading, spacing: 6) {
                                                Text(routing.label)
                                                    .font(.headline)
                                                    .foregroundStyle(.white)
                                                Text(routing.reason)
                                                    .font(.caption)
                                                    .foregroundStyle(.secondary)
                                                    .fixedSize(horizontal: false, vertical: true)
                                            }
                                            Spacer(minLength: 12)
                                            pill(readableDeliveryMode(routing.recommendedDelivery), color: accent)
                                        }

                                        HStack(spacing: 8) {
                                            if routing.focusActive {
                                                pill("Focus Active", color: .blue.opacity(0.82))
                                            }
                                            if routing.quietHours {
                                                pill("Quiet Hours", color: .white.opacity(0.35))
                                            }
                                            if routing.alertCount > 0 {
                                                pill("\(routing.alertCount) Alerts", color: .orange.opacity(0.88))
                                            }
                                            if routing.needsCount > 0 {
                                                pill("\(routing.needsCount) Needs", color: .yellow.opacity(0.82))
                                            }
                                        }

                                        if !routing.presentMembers.isEmpty {
                                            Text("Home presence: \(routing.presentMembers.joined(separator: ", "))")
                                                .font(.caption2)
                                                .foregroundStyle(.secondary)
                                        }

                                        ForEach(routing.lanes) { lane in
                                            HStack(alignment: .top, spacing: 10) {
                                                Circle()
                                                    .fill(lane.active ? accent : .white.opacity(0.2))
                                                    .frame(width: 8, height: 8)
                                                    .padding(.top, 5)
                                                VStack(alignment: .leading, spacing: 2) {
                                                    Text(lane.title)
                                                        .font(.caption.weight(.semibold))
                                                        .foregroundStyle(.white)
                                                    Text(lane.detail)
                                                        .font(.caption2)
                                                        .foregroundStyle(.secondary)
                                                }
                                                Spacer()
                                                if lane.active {
                                                    pill("Live", color: accent)
                                                }
                                            }
                                        }

                                        if let updatedAt = overview?.routing.updatedAt, !updatedAt.isEmpty {
                                            Text("Updated \(formatTimestamp(updatedAt))")
                                                .font(.caption2)
                                                .foregroundStyle(.secondary.opacity(0.75))
                                        }
                                    }
                                    .padding(14)
                                    .glassEffect(in: RoundedRectangle(cornerRadius: 18))
                                }

                                HStack(spacing: 10) {
                                    summaryMetric(title: "Pending", value: "\(overview?.summary.pending ?? notifications.filter { $0.status == "pending" }.count)")
                                    summaryMetric(title: "Active", value: "\(overview?.summary.total ?? notifications.count)")
                                    summaryMetric(title: "Events", value: "\(overview?.eventSummary.recentCount ?? events.count)")
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
        var issues: [String] = []

        do {
            let fetchedOverview = try await client.fetchNotificationCenterOverview()
            overview = fetchedOverview
            notifications = fetchedOverview.notifications
        } catch {
            overview = nil
            notifications = []
            issues.append("Inbox: \(describe(error))")
        }

        do {
            events = try await client.fetchRecentEvents(limit: 20)
        } catch {
            events = []
            issues.append("Events: \(describe(error))")
        }

        if !issues.isEmpty {
            errorMessage = issues.joined(separator: "  ")
        }
        isLoading = false
    }

    private func describe(_ error: Error) -> String {
        if let decodingError = error as? DecodingError {
            switch decodingError {
            case let .keyNotFound(key, context):
                return "Missing key '\(key.stringValue)' at \(codingPath(context.codingPath)): \(context.debugDescription)"
            case let .valueNotFound(_, context):
                return "Missing value at \(codingPath(context.codingPath)): \(context.debugDescription)"
            case let .typeMismatch(_, context):
                return "Type mismatch at \(codingPath(context.codingPath)): \(context.debugDescription)"
            case let .dataCorrupted(context):
                return "Corrupted data at \(codingPath(context.codingPath)): \(context.debugDescription)"
            @unknown default:
                break
            }
        }
        return error.localizedDescription
    }

    private func codingPath(_ path: [CodingKey]) -> String {
        let joined = path.map(\.stringValue).joined(separator: ".")
        return joined.isEmpty ? "root" : joined
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
            let result = try await client.resolveNotification(id)
            switch result.status {
            case "resolved":
                errorMessage = nil
            case "staged_for_review":
                errorMessage = result.boundaryReason?.isEmpty == false ? result.boundaryReason : "Notification action staged for review."
            case "blocked_by_boundary":
                errorMessage = result.boundaryReason?.isEmpty == false ? result.boundaryReason : "Notification action blocked by boundary."
            default:
                errorMessage = nil
            }
            await load()
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
                let result = try await client.snoozeNotification(id)
                switch result.status {
                case "snoozed":
                    errorMessage = nil
                case "staged_for_review":
                    errorMessage = result.boundaryReason?.isEmpty == false ? result.boundaryReason : "Notification action staged for review."
                case "blocked_by_boundary":
                    errorMessage = result.boundaryReason?.isEmpty == false ? result.boundaryReason : "Notification action blocked by boundary."
                default:
                    errorMessage = nil
                }
                await load()
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

    private func readableFocusMode(_ mode: String) -> String {
        switch mode {
        case "morning_brief":
            return "Morning Brief"
        case "work":
            return "Work Focus"
        case "daily_recap":
            return "Daily Recap"
        case "sleep":
            return "Sleep"
        case "personal":
            return "Personal Time"
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
