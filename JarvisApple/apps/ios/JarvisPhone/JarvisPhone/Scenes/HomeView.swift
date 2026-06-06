import SwiftUI
import HomeKit
import JarvisKit

// MARK: - HomeView  "The Control Room"

struct HomeView: View {

    @StateObject private var hk = HomeKitManager.shared
    @State private var serverState: HomeState?
    @State private var isLoadingServerState = false
    @State private var serverError: String?
    @State private var stagedHomeActionID: String?
    @State private var stagedHomeActionMessage: String?
    @State private var stagedLaneReviewID: String?
    @State private var stagedLaneReviewMessage: String?

    private let amber = Color.orange

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 14) {
                        liveStateSection

                        if !hk.isAuthorized {
                            setupState
                        } else if hk.accessories.isEmpty {
                            emptyState
                        } else {
                            contentView
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                }
            }
            .navigationTitle("Home")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    HStack(spacing: 6) {
                        // All lights off quick action
                        if !hk.lights.isEmpty {
                            Button {
                                Task {
                                    for light in hk.lights {
                                        await hk.setLightOn(light, on: false)
                                    }
                                }
                            } label: {
                                Label("All Off", systemImage: "lightbulb.slash.fill")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(amber)
                            }
                            .glassEffect(in: Capsule())
                        }

                        Button {
                            Task { await loadServerState() }
                        } label: {
                            if isLoadingServerState {
                                ProgressView().tint(amber).scaleEffect(0.8)
                            } else {
                                Image(systemName: "arrow.clockwise")
                                    .foregroundStyle(amber)
                            }
                        }
                        .glassEffect(in: Circle())
                    }
                }
            }
        }
        .task { await loadServerState() }
        .refreshable { await loadServerState() }
    }

    // MARK: - Content

    private var contentView: some View {
        VStack(spacing: 14) {
            // ── Status banner ──────────────────────────────────
            HStack(spacing: 14) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(hk.homes.first?.name ?? "Home")
                        .font(.title3.bold())
                        .foregroundStyle(.white)
                    Text("\(hk.accessories.count) devices paired")
                        .font(.caption)
                        .foregroundStyle(amber.opacity(0.8))
                }
                Spacer()
                Image(systemName: "house.fill")
                    .font(.system(size: 32))
                    .foregroundStyle(amber.opacity(0.7))
            }
            .padding(16)
            .glassEffect(in: RoundedRectangle(cornerRadius: 16))

            // ── Lights ─────────────────────────────────────────
            if !hk.lights.isEmpty {
                HomeSection(title: "Lights", icon: "lightbulb.fill", accent: amber) {
                    LazyVGrid(
                        columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 2),
                        spacing: 10
                    ) {
                        ForEach(hk.lights, id: \.uniqueIdentifier) { light in
                            LightTile(accessory: light)
                        }
                    }
                }
            }

            // ── Locks ──────────────────────────────────────────
            if !hk.locks.isEmpty {
                HomeSection(title: "Locks", icon: "lock.shield.fill", accent: .green) {
                    ForEach(hk.locks, id: \.uniqueIdentifier) { lock in
                        LockRow(accessory: lock)
                    }
                }
            }

            // ── Climate ────────────────────────────────────────
            if !hk.thermostats.isEmpty {
                HomeSection(title: "Climate", icon: "thermometer.medium", accent: Color(red: 0.4, green: 0.75, blue: 1.0)) {
                    ForEach(hk.thermostats, id: \.uniqueIdentifier) { thermo in
                        ThermostatRow(accessory: thermo)
                    }
                }
            }
        }
    }

    // MARK: - Setup / empty states

    private var liveStateSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                ZStack {
                    Circle()
                        .fill((serverError == nil ? amber : Color.red).opacity(0.12))
                        .frame(width: 42, height: 42)
                    Image(systemName: serverError == nil ? "dot.radiowaves.left.and.right" : "exclamationmark.triangle.fill")
                        .foregroundStyle(serverError == nil ? amber : .red)
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text("Live JARVIS Home")
                        .font(.subheadline.bold())
                        .foregroundStyle(.white)
                    Text(serverError ?? "Household state from the production JARVIS stack")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                if isLoadingServerState {
                    ProgressView().tint(amber)
                }
            }

            if let state = serverState {
                HStack(spacing: 10) {
                    liveMetric(title: "Present", value: state.presentMembers.isEmpty ? "0" : "\(state.presentMembers.count)")
                    liveMetric(title: "Lights", value: state.lightsOn.isEmpty ? "0" : "\(state.lightsOn.count)")
                    liveMetric(title: "Alerts", value: state.alerts.isEmpty ? "0" : "\(state.alerts.count)")
                }

                HStack(spacing: 10) {
                    liveMetric(title: "Inside", value: "\(Int(state.temperature.inside.rounded()))°")
                    liveMetric(title: "Target", value: "\(Int(state.temperature.target.rounded()))°")
                    liveMetric(title: "Mode", value: state.temperature.mode.isEmpty ? "—" : state.temperature.mode.capitalized)
                }

                if !state.presentMembers.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Present Members")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(amber)
                        Text(state.presentMembers.joined(separator: " • "))
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.82))
                    }
                }

                if !state.alerts.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Live Alerts")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.red)
                        ForEach(Array(state.alerts.enumerated()), id: \.offset) { _, alert in
                            VStack(alignment: .leading, spacing: 2) {
                                Text(alert.message)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                Text("\(alert.entity) · \(alert.state)")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }
                    }
                }

                if !state.actionItems.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Household Actions")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(amber)
                        ForEach(state.actionItems) { item in
                            VStack(alignment: .leading, spacing: 8) {
                                HStack(alignment: .top, spacing: 10) {
                                    Circle()
                                        .fill(actionColor(for: item.emphasis).opacity(0.18))
                                        .frame(width: 10, height: 10)
                                        .padding(.top, 4)
                                    VStack(alignment: .leading, spacing: 3) {
                                        Text(item.title)
                                            .font(.caption.weight(.semibold))
                                            .foregroundStyle(.white)
                                        Text(item.detail)
                                            .font(.caption2)
                                            .foregroundStyle(.secondary)
                                            .lineLimit(3)
                                    }
                                    Spacer()
                                    Button {
                                        Task { await stageHomeAction(item) }
                                    } label: {
                                        if stagedHomeActionID == item.id {
                                            ProgressView()
                                                .tint(amber)
                                                .scaleEffect(0.8)
                                        } else {
                                            Text("Stage")
                                                .font(.caption.weight(.semibold))
                                                .foregroundStyle(amber)
                                        }
                                    }
                                    .glassEffect(in: Capsule())
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }
                        if let stagedHomeActionMessage, !stagedHomeActionMessage.isEmpty {
                            Text(stagedHomeActionMessage)
                                .font(.caption2)
                                .foregroundStyle(amber.opacity(0.9))
                        }
                        if let stagedLaneReviewMessage, !stagedLaneReviewMessage.isEmpty {
                            Text(stagedLaneReviewMessage)
                                .font(.caption2)
                                .foregroundStyle(.cyan.opacity(0.9))
                        }
                    }
                }

                if let context = state.homeContext {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Household Context")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(amber)

                        HStack(spacing: 10) {
                            liveMetric(title: "Events", value: "\(context.agenda.todayEventCount)")
                            liveMetric(title: "Reminders", value: "\(context.attention.reminderCount)")
                            liveMetric(title: "Needs", value: "\(context.attention.needsCount)")
                        }

                        HStack(spacing: 10) {
                            liveMetric(title: "Inbox", value: "\(context.attention.unreadEmailCount)")
                            liveMetric(title: "Alerts", value: "\(context.attention.notificationCount)")
                            liveMetric(title: "Projects", value: "\(context.projects.activeWorkItemsCount)")
                        }

                        if !context.agenda.nextEventTitle.isEmpty {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(context.agenda.nextEventTitle)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                Text(context.agenda.nextEventStart.isEmpty ? "Upcoming family event" : context.agenda.nextEventStart)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                                if !context.agenda.nextEventLocation.isEmpty {
                                    Text(context.agenda.nextEventLocation)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.85))
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }

                        if !context.projects.topTitles.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Active Work")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(amber)
                                ForEach(context.projects.topTitles, id: \.self) { title in
                                    Text(title)
                                        .font(.caption)
                                        .foregroundStyle(.white.opacity(0.82))
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .padding(.vertical, 2)
                                }
                            }
                        }
                    }
                }

                if let homeOps = state.homeOps {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Home Ops")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(amber)

                        HStack(spacing: 10) {
                            liveMetric(title: "Unread", value: "\(homeOps.email.totalUnread)")
                            liveMetric(title: "Open Tasks", value: "\(homeOps.tasks.openCount)")
                            liveMetric(title: "Projects", value: "\(homeOps.projects.activeCount)")
                        }

                        HStack(spacing: 10) {
                            liveMetric(title: "Today", value: "\(homeOps.calendar.todayCount)")
                            liveMetric(title: "Overdue", value: "\(homeOps.tasks.overdueCount)")
                            liveMetric(title: "Signals", value: "\(homeOps.projects.unclassifiedSignalCount)")
                        }

                        if homeOps.email.totalUnread > 0 || homeOps.email.flaggedTotal > 0 {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Inbox")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                Text("Gmail \(homeOps.email.gmailUnread) · Outlook \(homeOps.email.outlookUnread) · Flagged \(homeOps.email.flaggedTotal)")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }

                        if !homeOps.tasks.topTitles.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Task Queue")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                ForEach(homeOps.tasks.topTitles, id: \.self) { title in
                                    Text(title)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.9))
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }

                        if !homeOps.projects.topTitles.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Active Projects")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                ForEach(homeOps.projects.topTitles, id: \.self) { title in
                                    Text(title)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.9))
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                }
                                if homeOps.projects.stalledCount > 0 {
                                    Text("\(homeOps.projects.stalledCount) stalled project" + (homeOps.projects.stalledCount == 1 ? "" : "s"))
                                        .font(.caption2)
                                        .foregroundStyle(Color.orange.opacity(0.88))
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }

                        if !homeOps.calendar.nextTitle.isEmpty {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Next Calendar Move")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                Text(homeOps.calendar.nextTitle)
                                    .font(.caption)
                                    .foregroundStyle(.white.opacity(0.9))
                                Text(homeOps.calendar.nextStart.isEmpty ? "Within the next 7 days" : homeOps.calendar.nextStart)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                                if !homeOps.calendar.nextLocation.isEmpty {
                                    Text(homeOps.calendar.nextLocation)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.85))
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }

                        if !homeOps.sync.connectedSources.isEmpty || !homeOps.sync.attentionSources.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Sync Health")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                if !homeOps.sync.connectedSources.isEmpty {
                                    Text("Connected: " + homeOps.sync.connectedSources.joined(separator: " • "))
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.9))
                                }
                                if !homeOps.sync.attentionSources.isEmpty {
                                    Text("Needs attention: " + homeOps.sync.attentionSources.joined(separator: " • "))
                                        .font(.caption2)
                                        .foregroundStyle(.orange.opacity(0.88))
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }
                    }
                }

                if let whileAway = state.whileYouWereAway {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("While You Were Away")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(amber)

                        Text(whileAway.headline)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white)

                        if !whileAway.summary.isEmpty {
                            Text(whileAway.summary)
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }

                        if !whileAway.laneReports.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                ForEach(whileAway.laneReports.prefix(3)) { lane in
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(lane.title)
                                            .font(.caption.weight(.semibold))
                                            .foregroundStyle(.white)
                                        Text(lane.summary)
                                            .font(.caption2)
                                            .foregroundStyle(.secondary.opacity(0.9))
                                            .lineLimit(2)
                                    }
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }

                        if !whileAway.stewardshipLanes.isEmpty {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Stewardship Lanes")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                ForEach(whileAway.stewardshipLanes.prefix(2)) { lane in
                                    homeStewardshipLaneCard(lane)
                                }
                            }
                        }

                        if let completion = whileAway.quietCompletions.first {
                            homeWhileAwayRow(
                                label: "Quiet Completion",
                                item: completion,
                                accent: .green
                            )
                        }

                        if let prepared = whileAway.preparedWork.first {
                            homeWhileAwayRow(
                                label: "Prepared For You",
                                item: prepared,
                                accent: .cyan
                            )
                        }

                        if let blocked = whileAway.blockedWork.first {
                            homeWhileAwayRow(
                                label: "Blocked Work",
                                item: blocked,
                                accent: .orange
                            )
                        }

                        if let recommendation = whileAway.recommendation {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Recommendation")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                Text(recommendation.title)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white.opacity(0.96))
                                Text(recommendation.summary)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary.opacity(0.9))
                                    .lineLimit(3)
                                if !recommendation.action.isEmpty {
                                    Text(recommendation.action)
                                        .font(.caption2.weight(.semibold))
                                        .foregroundStyle(Color.cyan.opacity(0.92))
                                        .lineLimit(2)
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }
                    }
                }

                if let continuity = state.continuity {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Carry Forward")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(amber)

                        HStack(spacing: 10) {
                            liveMetric(title: "Facts", value: "\(continuity.profileFactCount)")
                            liveMetric(
                                title: "Mode",
                                value: continuity.activeMode.isEmpty ? "—" : continuity.activeMode.replacingOccurrences(of: "_", with: " ").capitalized
                            )
                            liveMetric(title: "Rooms", value: continuity.primaryRooms.isEmpty ? "0" : "\(continuity.primaryRooms.count)")
                        }

                        if !continuity.guidanceLines.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Household Rhythm")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                ForEach(continuity.guidanceLines, id: \.self) { line in
                                    Text(line)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.9))
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }

                        if !continuity.longHorizonLines.isEmpty || !continuity.activeThreads.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Long Horizon")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                ForEach(continuity.longHorizonLines.prefix(2), id: \.self) { line in
                                    Text(line)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.9))
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                }
                                if !continuity.activeThreads.isEmpty {
                                    Text(continuity.activeThreads.joined(separator: " • "))
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.82))
                                        .lineLimit(2)
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }

                        if !continuity.primaryRooms.isEmpty || !continuity.morningRoom.isEmpty {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Where JARVIS Holds Continuity")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                if !continuity.primaryRooms.isEmpty {
                                    Text(continuity.primaryRooms.joined(separator: " • "))
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.9))
                                }
                                if !continuity.morningRoom.isEmpty {
                                    Text("Morning room: \(continuity.morningRoom)")
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.82))
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }

                        if !continuity.recentProfileFacts.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Durable Patterns")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                ForEach(continuity.recentProfileFacts) { fact in
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(fact.title)
                                            .font(.caption.weight(.semibold))
                                            .foregroundStyle(.white.opacity(0.94))
                                        Text(fact.summary)
                                            .font(.caption2)
                                            .foregroundStyle(.secondary.opacity(0.9))
                                    }
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }

                        if !continuity.recentFirstLight.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Recent First Light")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                ForEach(continuity.recentFirstLight) { moment in
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(moment.label)
                                            .font(.caption.weight(.semibold))
                                            .foregroundStyle(.white.opacity(0.94))
                                        Text(moment.summary)
                                            .font(.caption2)
                                            .foregroundStyle(.secondary.opacity(0.9))
                                    }
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }
                    }
                }
            } else if serverError == nil {
                Text("Loading live house state from JARVIS…")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private var setupState: some View {
        VStack(spacing: 20) {
            Image(systemName: "house.circle")
                .font(.system(size: 60))
                .foregroundStyle(amber.opacity(0.5))
            Text("Connect HomeKit")
                .font(.title3.bold())
                .foregroundStyle(.white)
            Text("JARVIS will control your lights, locks, and climate through HomeKit.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Text("Add your home in the Apple Home app first, then return here.")
                .font(.caption)
                .foregroundStyle(.white.opacity(0.4))
                .multilineTextAlignment(.center)
        }
        .padding(32)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .frame(maxWidth: .infinity)
    }

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "house.fill")
                .font(.system(size: 48))
                .foregroundStyle(amber.opacity(0.35))
            Text("No devices found")
                .font(.title3.bold())
                .foregroundStyle(.white)
            Text("Add accessories in the Apple Home app.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(24)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
    }

    private func liveMetric(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value)
                .font(.headline.bold())
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .glassEffect(in: RoundedRectangle(cornerRadius: 14))
    }

    private func loadServerState() async {
        isLoadingServerState = true
        defer { isLoadingServerState = false }
        do {
            serverState = try await AppleAPIClient.shared.fetchHomeState()
            serverError = nil
        } catch {
            serverError = error.localizedDescription
        }
    }

    private func stageHomeAction(_ item: HomeActionItem) async {
        stagedHomeActionID = item.id
        defer { stagedHomeActionID = nil }
        do {
            let response = try await AppleAPIClient.shared.sendHomeCommand(
                HomeCommand(command: item.command, entityId: item.entityId, service: item.service)
            )
            switch response.status {
            case "executed_live":
                stagedHomeActionMessage = "Executed live: \(item.title)"
            case "blocked_by_boundary":
                stagedHomeActionMessage = response.boundaryReason ?? "Blocked by trust boundary."
            default:
                let detail = response.boundaryDecision == "stage"
                    ? "Queued for approval: \(item.title)"
                    : "Queued: \(item.title)"
                stagedHomeActionMessage = detail
            }
            await loadServerState()
        } catch {
            stagedHomeActionMessage = error.localizedDescription
        }
    }

    private func actionColor(for emphasis: String) -> Color {
        switch emphasis {
        case "high":
            return .red
        case "medium":
            return amber
        default:
            return .cyan
        }
    }

    private func homeWhileAwayRow(
        label: String,
        item: WhileYouWereAwayRow,
        accent: Color
    ) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.caption.weight(.semibold))
                .foregroundStyle(accent)
            Text(item.title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.white)
            Text("\(item.agent) · \(item.lane)")
                .font(.caption2)
                .foregroundStyle(.secondary.opacity(0.85))
            Text(item.summary)
                .font(.caption2)
                .foregroundStyle(.secondary.opacity(0.9))
                .lineLimit(3)
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
    }

    private func homeStewardshipLaneCard(_ lane: WhileYouWereAwayStewardshipLane) -> some View {
        let reportLine = lane.reportSummaries.first?.summary ?? lane.summary
        let primitive = lane.executionPrimitive
        return VStack(alignment: .leading, spacing: 8) {
            Text(lane.title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.white)
            Text(reportLine)
                .font(.caption2)
                .foregroundStyle(.secondary.opacity(0.9))
                .lineLimit(2)
            Text("Prepared \(lane.preparedWork.count) · Decisions \(lane.decisionCards.count) · Drift \(lane.driftCards.count)")
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.cyan.opacity(0.92))
            if let primitive, !primitive.routeSummary.isEmpty {
                Text(primitive.routeSummary)
                    .font(.caption2)
                    .foregroundStyle(.secondary.opacity(0.88))
                    .lineLimit(2)
            }
            if let primitive {
                HStack(spacing: 8) {
                    Text(primitive.laneStatus.replacingOccurrences(of: "-", with: " ").capitalized)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(amber.opacity(0.92))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 5)
                        .background(.white.opacity(0.06), in: Capsule())
                    Spacer()
                    Button {
                        Task { await stageStewardshipLaneReview(lane.id) }
                    } label: {
                        if stagedLaneReviewID == lane.id {
                            ProgressView()
                                .tint(amber)
                                .scaleEffect(0.8)
                        } else {
                            Text("Stage Review")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(amber)
                        }
                    }
                    .glassEffect(in: Capsule())
                    .disabled(stagedLaneReviewID == lane.id)
                }
                Text(primitive.actionDetail)
                    .font(.caption2)
                    .foregroundStyle(.secondary.opacity(0.82))
                    .lineLimit(2)
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
    }

    private func stageStewardshipLaneReview(_ laneId: String) async {
        stagedLaneReviewID = laneId
        stagedLaneReviewMessage = nil
        defer { stagedLaneReviewID = nil }
        do {
            let result = try await AppleAPIClient.shared.stageStewardshipLaneReview(laneId)
            if result.status == "review_staged" {
                stagedLaneReviewMessage = "\(result.laneTitle) is queued in \(result.reviewSurface.capitalized) for review."
            } else {
                stagedLaneReviewMessage = result.boundaryReason
            }
            await loadServerState()
        } catch {
            stagedLaneReviewMessage = error.localizedDescription
        }
    }
}

// MARK: - Home section

private struct HomeSection<Content: View>: View {
    let title: String
    let icon: String
    let accent: Color
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(title, systemImage: icon)
                .font(.caption.weight(.semibold))
                .foregroundStyle(accent)
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Light tile

private struct LightTile: View {
    let accessory: HMAccessory

    @State private var isOn: Bool = false

    private var powerChar: HMCharacteristic? {
        accessory.services
            .first(where: { $0.serviceType == HMServiceTypeLightbulb })?
            .characteristics
            .first(where: { $0.characteristicType == HMCharacteristicTypePowerState })
    }

    var body: some View {
        Button {
            isOn.toggle()
            Task { await HomeKitManager.shared.setLightOn(accessory, on: isOn) }
        } label: {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Image(systemName: isOn ? "lightbulb.fill" : "lightbulb")
                        .font(.system(size: 22))
                        .foregroundStyle(isOn ? Color.orange : .white.opacity(0.35))
                        .shadow(color: isOn ? Color.orange.opacity(0.6) : .clear, radius: 8)
                    Spacer()
                    Circle()
                        .fill(isOn ? Color.orange : Color.white.opacity(0.1))
                        .frame(width: 10, height: 10)
                }
                Text(accessory.name)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
                Text(isOn ? "On" : "Off")
                    .font(.caption2)
                    .foregroundStyle(isOn ? Color.orange.opacity(0.8) : .white.opacity(0.3))
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .glassEffect(in: RoundedRectangle(cornerRadius: 14))
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .stroke(isOn ? Color.orange.opacity(0.4) : .clear, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .onAppear {
            isOn = powerChar?.value as? Bool ?? false
        }
    }
}

// MARK: - Lock row

private struct LockRow: View {
    let accessory: HMAccessory

    private var isLocked: Bool {
        let char = accessory.services
            .first(where: { $0.serviceType == HMServiceTypeLockMechanism })?
            .characteristics
            .first(where: { $0.characteristicType == HMCharacteristicTypeCurrentLockMechanismState })
        let val = char?.value as? Int
        return val == 1  // 1 = secured
    }

    var body: some View {
        HStack(spacing: 14) {
            ZStack {
                Circle()
                    .fill(isLocked ? Color.green.opacity(0.15) : Color.orange.opacity(0.15))
                    .frame(width: 44, height: 44)
                Image(systemName: isLocked ? "lock.fill" : "lock.open.fill")
                    .font(.system(size: 18))
                    .foregroundStyle(isLocked ? .green : .orange)
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(accessory.name)
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(.white)
                Text(isLocked ? "Secured" : "Unlocked")
                    .font(.caption)
                    .foregroundStyle(isLocked ? .green.opacity(0.8) : .orange.opacity(0.8))
            }
            Spacer()
        }
        .padding(.vertical, 2)
    }
}

// MARK: - Thermostat row

private struct ThermostatRow: View {
    let accessory: HMAccessory

    private var targetTempC: Double? {
        accessory.services
            .first(where: { $0.serviceType == HMServiceTypeThermostat })?
            .characteristics
            .first(where: { $0.characteristicType == HMCharacteristicTypeTargetTemperature })?
            .value as? Double
    }

    private var tempFString: String {
        guard let c = targetTempC else { return "—" }
        let f = c * 9 / 5 + 32
        return String(format: "%.0f°F", f)
    }

    var body: some View {
        HStack(spacing: 14) {
            ZStack {
                Circle()
                    .fill(Color(red: 0.4, green: 0.75, blue: 1.0).opacity(0.12))
                    .frame(width: 44, height: 44)
                Image(systemName: "thermometer.medium")
                    .font(.system(size: 18))
                    .foregroundStyle(Color(red: 0.4, green: 0.75, blue: 1.0))
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(accessory.name)
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(.white)
                Text("Target: \(tempFString)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Text(tempFString)
                .font(.title3.bold().monospacedDigit())
                .foregroundStyle(Color(red: 0.4, green: 0.75, blue: 1.0))
        }
        .padding(.vertical, 2)
    }
}

#Preview {
    HomeView()
}
