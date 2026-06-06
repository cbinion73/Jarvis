import SwiftUI
import JarvisKit
import SafariServices

// MARK: - CatalystView  "The Workshop"
// Mantis · Personal Workflow Intelligence

struct CatalystView: View {

    @State private var overview: CatalystOverview?
    @State private var opsOverview: CatalystOpsOverview?
    @State private var isLoading  = false
    @State private var error: String?
    @State private var opsMessage: String?
    @State private var actionInFlight: String?
    @State private var selectedModule: CatalystOpsModule?

    private let blue = Color(red: 0.25, green: 0.55, blue: 1.0)
    private let opsModules = CatalystOpsModule.allCases

    var body: some View {
        NavigationStack {
            ZStack {
                // Electric blue depth
                ZStack {
                    Color.black
                    LinearGradient(
                        colors: [Color(red: 0.02, green: 0.04, blue: 0.12), Color.black],
                        startPoint: .top,
                        endPoint: UnitPoint(x: 0.5, y: 0.5)
                    )
                }
                .ignoresSafeArea()

                Group {
                    if isLoading && overview == nil {
                        loadingView
                    } else if let ov = overview {
                        contentView(ov)
                    } else if let e = error {
                        errorView(e)
                    } else {
                        loadingView
                    }
                }
            }
            .navigationTitle("Catalyst")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { Task { await load() } } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .glassEffect(in: Circle())
                }
            }
        }
        .task { await load() }
        .refreshable { await load() }
        .sheet(item: $selectedModule) { module in
            OpsModuleRouteSheet(module: module)
        }
    }

    // MARK: - Loading

    private var loadingView: some View {
        VStack(spacing: 16) {
            Image(systemName: "gearshape.2.fill")
                .font(.system(size: 36))
                .foregroundStyle(blue.opacity(0.4))
                .symbolEffect(.rotate)
            Text("Loading Catalyst…")
                .font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Content

    @ViewBuilder
    private func contentView(_ ov: CatalystOverview) -> some View {
        ScrollView {
            VStack(spacing: 14) {
                opsCommandHeader(overview: ov)

                opsStoryboardStrip

                opsNativeStudio

                opsLauncherGrid(overview: ov)

                CatSection(title: "Workspace Pulse", icon: "bolt.horizontal.circle.fill", accent: blue) {
                    HStack(spacing: 10) {
                        PortfolioTile(label: "lanes", count: ov.lanes.count, accent: blue)
                        PortfolioTile(label: "connectors", count: ov.connectors.count, accent: blue)
                    }
                    HStack(spacing: 10) {
                        PortfolioTile(label: "projects", count: ov.liveWorkspace.projectsCount, accent: blue)
                        PortfolioTile(label: "tasks", count: ov.liveWorkspace.tasksCount, accent: blue)
                    }
                    HStack(spacing: 10) {
                        PortfolioTile(label: "calendar", count: ov.liveWorkspace.calendarCount, accent: blue)
                        PortfolioTile(label: "email", count: ov.liveWorkspace.emailCount, accent: blue)
                    }
                    Text(ov.liveWorkspace.live ? "Live workspace is connected" : "Workspace snapshot is local / inferred")
                        .font(.caption2)
                        .foregroundStyle(ov.liveWorkspace.live ? .green.opacity(0.9) : .secondary)
                }

                if !ov.activeWork.isEmpty {
                    CatSection(title: "Active Work", icon: "hammer.fill", accent: blue) {
                        ForEach(ov.activeWork) { item in
                            WorkItemRow(item: item, accent: blue)
                            if item.id != ov.activeWork.last?.id {
                                Divider().opacity(0.2)
                            }
                        }
                    }
                } else {
                    emptyWork
                }

                if !ov.lanes.isEmpty {
                    CatSection(title: "Portfolio Lanes", icon: "square.grid.2x2.fill", accent: blue.opacity(0.88)) {
                        ForEach(ov.lanes) { lane in
                            LaneRow(lane: lane)
                            if lane.id != ov.lanes.last?.id {
                                Divider().opacity(0.2)
                            }
                        }
                    }
                }

                if !ov.signals.isEmpty {
                    CatSection(title: "Signals", icon: "antenna.radiowaves.left.and.right", accent: blue.opacity(0.8)) {
                        ForEach(ov.signals) { sig in
                            SignalRow(signal: sig)
                            if sig.id != ov.signals.last?.id {
                                Divider().opacity(0.2)
                            }
                        }
                    }
                }

                if !ov.connectors.isEmpty {
                    CatSection(title: "Connectors", icon: "point.3.connected.trianglepath.dotted", accent: blue.opacity(0.8)) {
                        ForEach(ov.connectors) { connector in
                            ConnectorRow(connector: connector)
                            if connector.id != ov.connectors.last?.id {
                                Divider().opacity(0.2)
                            }
                        }
                    }
                }

                if !ov.workflowCounts.isEmpty {
                    CatSection(title: "Workflow Throughput", icon: "speedometer", accent: blue) {
                        LazyVGrid(
                            columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 2),
                            spacing: 10
                        ) {
                            ForEach(ov.workflowCounts.sorted(by: { $0.key < $1.key }), id: \.key) { key, val in
                                PortfolioTile(label: key.replacingOccurrences(of: "_", with: " "), count: val, accent: blue)
                            }
                        }
                    }
                }

                if !ov.continuity.guidanceLines.isEmpty || !ov.continuity.recentProfileFacts.isEmpty || !ov.continuity.recentFirstLight.isEmpty || !ov.continuity.activeDomains.isEmpty {
                    CatSection(title: "Carry Forward", icon: "point.3.connected.trianglepath.dotted", accent: blue.opacity(0.88)) {
                        HStack(spacing: 10) {
                            PortfolioTile(label: "facts", count: ov.continuity.profileFactCount, accent: blue)
                            PortfolioTile(label: "domains", count: ov.continuity.activeDomains.count, accent: blue)
                        }

                        if !ov.continuity.hottestWorkflow.isEmpty || !ov.continuity.briefingStyle.isEmpty {
                            VStack(alignment: .leading, spacing: 4) {
                                if !ov.continuity.hottestWorkflow.isEmpty {
                                    Text("Hottest workflow: \(ov.continuity.hottestWorkflow.replacingOccurrences(of: "_", with: " ").capitalized)")
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.95))
                                }
                                if !ov.continuity.briefingStyle.isEmpty {
                                    Text("Briefing style: \(ov.continuity.briefingStyle.replacingOccurrences(of: "_", with: " ").capitalized)")
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.95))
                                }
                            }
                        }

                        if !ov.continuity.activeDomains.isEmpty {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Active Domains")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white.opacity(0.92))
                                Text(ov.continuity.activeDomains.joined(separator: " • "))
                                    .font(.caption2)
                                    .foregroundStyle(.secondary.opacity(0.95))
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }

                        if !ov.continuity.guidanceLines.isEmpty {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Workspace Rhythm")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white.opacity(0.92))
                                ForEach(ov.continuity.guidanceLines, id: \.self) { line in
                                    Text(line)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.95))
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }

                        if !ov.continuity.recentProfileFacts.isEmpty {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Durable Patterns")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white.opacity(0.92))
                                ForEach(ov.continuity.recentProfileFacts) { fact in
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(fact.title)
                                            .font(.caption.weight(.medium))
                                            .foregroundStyle(.white.opacity(0.92))
                                        Text(fact.summary)
                                            .font(.caption2)
                                            .foregroundStyle(.secondary.opacity(0.95))
                                    }
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }

                        if !ov.continuity.recentFirstLight.isEmpty {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Recent First Light")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white.opacity(0.92))
                                ForEach(ov.continuity.recentFirstLight) { moment in
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(moment.label)
                                            .font(.caption.weight(.medium))
                                            .foregroundStyle(.white.opacity(0.92))
                                        Text(moment.summary)
                                            .font(.caption2)
                                            .foregroundStyle(.secondary.opacity(0.95))
                                    }
                                }
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }
                    }
                }

                if !ov.latestRuns.isEmpty {
                    CatSection(title: "Latest Runs", icon: "clock.arrow.circlepath", accent: blue.opacity(0.88)) {
                        ForEach(ov.latestRuns) { run in
                            RunRow(run: run)
                            if run.id != ov.latestRuns.last?.id {
                                Divider().opacity(0.2)
                            }
                        }
                    }
                }

                if !ov.portfolio.summaryCounts.isEmpty || !ov.portfolio.mission.isEmpty {
                    CatSection(title: "Portfolio", icon: "chart.bar.xaxis", accent: blue) {
                        if !ov.portfolio.mission.isEmpty {
                            Text(ov.portfolio.mission)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .padding(.bottom, 2)
                        }
                        LazyVGrid(
                            columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 2),
                            spacing: 10
                        ) {
                            ForEach(ov.portfolio.summaryCounts.sorted(by: { $0.key < $1.key }), id: \.key) { key, val in
                                PortfolioTile(label: key, count: val, accent: blue)
                            }
                        }
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    private func opsCommandHeader(overview: CatalystOverview) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("JARVIS Catalyst Experience")
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                        .foregroundStyle(.white)
                    Text("Plans become action here. Mission pressure, approvals, recovery, continuity, and supervision are all reachable through the real product, while the native ops studio handles the fastest loops on-device.")
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.72))
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 8) {
                    opsBadge(
                        title: overview.liveWorkspace.live ? "Hosted Live" : "Local Snapshot",
                        detail: overview.liveWorkspace.live ? "jarvis.teambinion.org" : "Fallback workspace state",
                        tint: overview.liveWorkspace.live ? .green : .orange
                    )
                    opsBadge(
                        title: "\(opsModules.count) Lanes",
                        detail: "Operational routes ready",
                        tint: blue
                    )
                }
            }

            HStack(spacing: 10) {
                actionCapsule(title: "Command Center", icon: "square.grid.2x2.fill") {
                    selectedModule = .commandCenter
                }
                actionCapsule(title: "Approvals", icon: "checklist.checked") {
                    selectedModule = .approvalQueue
                }
                actionCapsule(title: "Reload", icon: "arrow.clockwise") {
                    Task { await load() }
                }
                actionCapsule(title: "Recovery", icon: "cross.case.fill") {
                    selectedModule = .recovery
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(
            LinearGradient(
                colors: [Color(red: 0.03, green: 0.08, blue: 0.18), Color.black],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 24, style: .continuous)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .stroke(Color.white.opacity(0.08), lineWidth: 1)
        )
    }

    private var opsStoryboardStrip: some View {
        let frames: [(String, String, String, Color)] = [
            ("1", "Operations", "See what is running, staged, and asking for intervention.", .cyan),
            ("2", "Workflow", "Open the live route-backed modules that still run best in the hosted product.", blue),
            ("3", "Agent Execution", "Track active missions and recent continuity without losing the native shell.", .orange),
            ("4", "Draft To Live", "Move the right lane forward with shared focus and mission actions.", .green),
            ("5", "Intervention", "Handle approvals and recovery loops from the phone before drift grows.", .pink),
            ("6", "Voice", "Use JARVIS as the command layer while the same operational routes stay one tap away.", Color.white.opacity(0.82)),
        ]
        return ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 10) {
                ForEach(Array(frames.enumerated()), id: \.offset) { _, frame in
                    VStack(alignment: .leading, spacing: 8) {
                        HStack(spacing: 8) {
                            Text(frame.0)
                                .font(.caption2.weight(.bold))
                                .foregroundStyle(frame.3)
                                .frame(width: 24, height: 24)
                                .background(frame.3.opacity(0.14), in: Circle())
                            Text(frame.1)
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.white)
                        }
                        Text(frame.2)
                            .font(.caption2)
                            .foregroundStyle(.white.opacity(0.62))
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .frame(width: 186, alignment: .leading)
                    .padding(12)
                    .background(.white.opacity(0.035), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 16, style: .continuous)
                            .stroke(Color.white.opacity(0.06), lineWidth: 1)
                    )
                }
            }
        }
    }

    private func opsLauncherGrid(overview: CatalystOverview) -> some View {
        CatSection(title: "Level 3 Ops Access", icon: "square.grid.3x3.topleft.filled", accent: blue) {
            Text("These cards open the real operational routes inside the phone app, so the still-web-heavy modules are usable on-device instead of existing only on desktop.")
                .font(.caption)
                .foregroundStyle(.secondary)

            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 2), spacing: 10) {
                ForEach(opsModules) { module in
                    Button {
                        selectedModule = module
                    } label: {
                        opsModuleCard(module: module, overview: overview)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var opsNativeStudio: some View {
        CatSection(title: "Native Ops Studio", icon: "switch.2", accent: blue.opacity(0.92)) {
            if let opsOverview {
                VStack(alignment: .leading, spacing: 12) {
                    HStack(alignment: .top, spacing: 10) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Shared Focus")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.white.opacity(0.88))
                            Text(opsOverview.currentFocus.module)
                                .font(.title3.weight(.bold))
                                .foregroundStyle(.white)
                            Text(opsOverview.currentFocus.reason)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        Spacer()
                        VStack(alignment: .trailing, spacing: 6) {
                            opsMetricPill(label: "approvals", value: opsOverview.counts.approvalCount)
                            opsMetricPill(label: "recovery", value: opsOverview.counts.recoveryCaseCount)
                            opsMetricPill(label: "agents", value: opsOverview.counts.agentOpsCount)
                            opsMetricPill(label: "supervision", value: opsOverview.counts.supervisionCount)
                        }
                    }

                    if let opsMessage, !opsMessage.isEmpty {
                        Text(opsMessage)
                            .font(.caption2)
                            .foregroundStyle(.white.opacity(0.72))
                            .padding(.horizontal, 10)
                            .padding(.vertical, 8)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        Text("Focus Moves")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white.opacity(0.88))
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                ForEach(opsOverview.focusCandidates.prefix(6)) { candidate in
                                    Button {
                                        Task { await setCatalystFocus(candidate) }
                                    } label: {
                                        VStack(alignment: .leading, spacing: 3) {
                                            Text(candidate.label)
                                                .font(.caption.weight(.semibold))
                                            Text(candidate.module)
                                                .font(.caption2)
                                                .foregroundStyle(.white.opacity(0.62))
                                        }
                                        .foregroundStyle(.white)
                                        .padding(.horizontal, 12)
                                        .padding(.vertical, 10)
                                        .background(.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                                    }
                                    .buttonStyle(.plain)
                                    .disabled(actionInFlight != nil)
                                    .opacity(actionInFlight != nil ? 0.7 : 1.0)
                                }
                            }
                        }
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        Text("Approval Lane")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white.opacity(0.88))
                        if opsOverview.approvals.isEmpty {
                            opsEmptyCard("No approvals are waiting right now.")
                        } else {
                            ForEach(opsOverview.approvals.prefix(3)) { approval in
                                opsApprovalRow(approval)
                            }
                        }
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        Text("Recovery Loops")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white.opacity(0.88))
                        if opsOverview.recoveryCases.isEmpty {
                            opsEmptyCard("No durable recovery cases need attention right now.")
                        } else {
                            ForEach(opsOverview.recoveryCases.prefix(3)) { entry in
                                opsRecoveryRow(entry)
                            }
                        }
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        Text("Agent Ops")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white.opacity(0.88))
                        if opsOverview.agentOps.isEmpty {
                            opsEmptyCard("No agent runs need a native push right now.")
                        } else {
                            ForEach(opsOverview.agentOps.prefix(3)) { agent in
                                opsAgentRow(agent)
                            }
                        }
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        Text("Supervision")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white.opacity(0.88))
                        if opsOverview.supervisionItems.isEmpty {
                            opsEmptyCard("No supervision reviews are staged in the native lane right now.")
                        } else {
                            ForEach(opsOverview.supervisionItems.prefix(3)) { item in
                                opsSupervisionRow(item)
                            }
                        }
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        Text("Mission Board")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white.opacity(0.88))
                        if opsOverview.missions.isEmpty {
                            opsEmptyCard("No active missions are waiting in the native studio right now.")
                        } else {
                            ForEach(opsOverview.missions.prefix(3)) { mission in
                                opsMissionRow(mission)
                            }
                        }
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        Text("Recent Continuity")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white.opacity(0.88))
                        if opsOverview.recentActivity.isEmpty {
                            opsEmptyCard("Native ops actions will echo back here when they run.")
                        } else {
                            ForEach(opsOverview.recentActivity.prefix(4)) { entry in
                                HStack(alignment: .top, spacing: 10) {
                                    VStack(alignment: .leading, spacing: 3) {
                                        Text(entry.title)
                                            .font(.caption.weight(.semibold))
                                            .foregroundStyle(.white)
                                        Text([entry.detail, entry.routeLabel].filter { !$0.isEmpty }.joined(separator: " · "))
                                            .font(.caption2)
                                            .foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                    Button {
                                        Task { await promoteActivityEntry(entry) }
                                    } label: {
                                        Text("Promote")
                                            .font(.caption2.weight(.semibold))
                                            .foregroundStyle(.white)
                                            .padding(.horizontal, 10)
                                            .padding(.vertical, 8)
                                            .background(blue.opacity(0.85), in: Capsule())
                                    }
                                    .buttonStyle(.plain)
                                    .disabled(actionInFlight != nil)
                                    .opacity(actionInFlight != nil ? 0.7 : 1.0)
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(10)
                                .background(.white.opacity(0.035), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                            }
                        }
                    }
                }
            } else if isLoading {
                HStack(spacing: 10) {
                    ProgressView().tint(.white)
                    Text("Loading native ops studio…")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                opsEmptyCard(opsMessage ?? "Native ops studio is unavailable for the moment.")
            }
        }
    }

    private func opsModuleCard(module: CatalystOpsModule, overview: CatalystOverview) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top) {
                Image(systemName: module.icon)
                    .foregroundStyle(module.tint)
                    .font(.headline)
                Spacer()
                Text(module.badgeText(overview: overview))
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(module.tint)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(module.tint.opacity(0.12), in: Capsule())
            }

            Text(module.title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.white)

            Text(module.phoneSummary)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.66))
                .fixedSize(horizontal: false, vertical: true)

            HStack {
                Text(module.routePath)
                    .font(.caption2.monospaced())
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                Spacer()
                Image(systemName: "arrow.up.right")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.white.opacity(0.75))
            }
        }
        .frame(maxWidth: .infinity, minHeight: 140, alignment: .leading)
        .padding(12)
        .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(Color.white.opacity(0.06), lineWidth: 1)
        )
    }

    private var emptyWork: some View {
        HStack(spacing: 10) {
            Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
            Text("No active work items")
                .font(.subheadline).foregroundStyle(.secondary)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .glassEffect(in: RoundedRectangle(cornerRadius: 14))
    }

    // MARK: - Error

    private func errorView(_ msg: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 44)).foregroundStyle(blue)
            Text("Catalyst unavailable")
                .font(.headline).foregroundStyle(.white)
            Text(msg).font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
            Button("Retry") { Task { await load() } }
                .buttonStyle(.borderedProminent).tint(blue)
        }
        .padding(24)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Fetch

    private func load() async {
        isLoading = true
        error = nil
        do {
            overview = try await AppleAPIClient.shared.fetchCatalyst()
            await loadOpsStudio()
        } catch {
            self.error = error.localizedDescription
        }
        isLoading = false
    }

    private func loadOpsStudio() async {
        do {
            opsOverview = try await AppleAPIClient.shared.fetchCatalystOps()
            if actionInFlight == nil, opsMessage?.hasPrefix("Native ops studio is unavailable") == true {
                opsMessage = nil
            }
        } catch {
            opsOverview = nil
            opsMessage = "Native ops studio is unavailable: \(error.localizedDescription)"
        }
    }

    private func setCatalystFocus(_ candidate: CatalystOpsFocusCandidate) async {
        actionInFlight = "focus:\(candidate.id)"
        opsMessage = "Promoting \(candidate.module) into shared focus…"
        defer { actionInFlight = nil }
        do {
            _ = try await AppleAPIClient.shared.saveCatalystProgressFocus(
                module: candidate.module,
                route: candidate.route,
                reason: "Catalyst promoted \(candidate.module) from the native ops studio."
            )
            await loadOpsStudio()
            opsMessage = "Shared focus now points at \(candidate.module)."
        } catch {
            opsMessage = "Unable to move focus: \(error.localizedDescription)"
        }
    }

    private func approveCatalystApproval(_ approval: CatalystApprovalEntry) async {
        actionInFlight = "approval:\(approval.id)"
        opsMessage = "Approving \(approval.title)…"
        defer { actionInFlight = nil }
        do {
            _ = try await AppleAPIClient.shared.approveCatalystApproval(approval.requestId)
            await loadOpsStudio()
            opsMessage = "Approved \(approval.title)."
        } catch {
            opsMessage = "Unable to approve \(approval.title): \(error.localizedDescription)"
        }
    }

    private func executeCatalystRecovery(_ entry: CatalystRecoveryCaseEntry) async {
        actionInFlight = "recovery:\(entry.id)"
        opsMessage = "\(entry.nextActionLabel) for \(entry.title)…"
        defer { actionInFlight = nil }
        do {
            _ = try await AppleAPIClient.shared.executeCatalystRecoveryCase(
                entry.caseId,
                actionType: entry.nextActionType,
                note: "Catalyst ran \(entry.nextActionLabel.lowercased()) from the native ops studio."
            )
            await loadOpsStudio()
            opsMessage = "\(entry.nextActionLabel) finished for \(entry.title)."
        } catch {
            opsMessage = "Unable to update recovery case: \(error.localizedDescription)"
        }
    }

    private func remediateCatalystRecovery(_ entry: CatalystRecoveryCaseEntry) async {
        actionInFlight = "recovery-remediation:\(entry.id)"
        opsMessage = "\(entry.remediationActionLabel) for \(entry.title)…"
        defer { actionInFlight = nil }
        do {
            _ = try await AppleAPIClient.shared.remediateCatalystRecoveryCase(
                entry.caseId,
                actionType: entry.remediationActionType,
                note: "Catalyst ran \(entry.remediationActionLabel.lowercased()) from the native ops studio."
            )
            await loadOpsStudio()
            opsMessage = "\(entry.remediationActionLabel) finished for \(entry.title)."
        } catch {
            opsMessage = "Unable to run recovery remediation: \(error.localizedDescription)"
        }
    }

    private func advanceCatalystRecoveryPlan(_ entry: CatalystRecoveryCaseEntry) async {
        actionInFlight = "recovery-plan:\(entry.id)"
        opsMessage = "\(entry.planActionLabel) for \(entry.title)…"
        defer { actionInFlight = nil }
        do {
            _ = try await AppleAPIClient.shared.executeNextCatalystRecoveryPlanStep(
                entry.caseId,
                note: "Catalyst advanced the next healing step from the native ops studio."
            )
            await loadOpsStudio()
            opsMessage = "\(entry.planActionLabel) finished for \(entry.title)."
        } catch {
            opsMessage = "Unable to advance recovery plan: \(error.localizedDescription)"
        }
    }

    private func queueCatalystAgentRun(_ agent: CatalystAgentOpsEntry) async {
        actionInFlight = "agent:\(agent.id)"
        opsMessage = "Queueing \(agent.name)…"
        defer { actionInFlight = nil }
        do {
            _ = try await AppleAPIClient.shared.queueCatalystAgentRun(agent.agentId)
            await loadOpsStudio()
            opsMessage = "\(agent.name) is queued for execution."
        } catch {
            opsMessage = "Unable to queue \(agent.name): \(error.localizedDescription)"
        }
    }

    private func resolveCatalystSupervision(_ item: CatalystSupervisionEntry, action: String) async {
        actionInFlight = "supervision:\(item.id):\(action)"
        let verb = action == "approve" ? item.approveLabel : item.rejectLabel
        opsMessage = "\(verb) \(item.title)…"
        defer { actionInFlight = nil }
        do {
            let reason = action == "approve"
                ? "Catalyst approved \(item.title) from the native supervision lane."
                : "Catalyst rejected \(item.title) from the native supervision lane to request a safer path."
            _ = try await AppleAPIClient.shared.resolveCatalystSupervision(
                item.requestId,
                action: action,
                reason: reason
            )
            await loadOpsStudio()
            opsMessage = "\(verb) finished for \(item.title)."
        } catch {
            opsMessage = "Unable to update supervision review: \(error.localizedDescription)"
        }
    }

    private func updateCatalystMission(_ mission: CatalystMissionEntry, status: String, note: String) async {
        actionInFlight = "mission:\(mission.id)"
        let verb = status == "completed" ? "Completing" : "Moving"
        opsMessage = "\(verb) \(mission.title)…"
        defer { actionInFlight = nil }
        do {
            _ = try await AppleAPIClient.shared.updateCatalystMissionStatus(
                mission.missionId,
                status: status,
                note: note
            )
            await loadOpsStudio()
            opsMessage = "\(mission.title) updated to \(status)."
        } catch {
            opsMessage = "Unable to update mission \(mission.title): \(error.localizedDescription)"
        }
    }

    private func promoteActivityEntry(_ entry: CatalystOpsActivityEntry) async {
        actionInFlight = "activity:\(entry.id)"
        let target = moduleName(for: entry)
        opsMessage = "Promoting \(entry.title) into shared focus…"
        defer { actionInFlight = nil }
        do {
            _ = try await AppleAPIClient.shared.saveCatalystProgressFocus(
                module: target,
                route: entry.relatedRoute.isEmpty ? "/activity-center" : entry.relatedRoute,
                reason: entry.detail.isEmpty ? "Catalyst promoted a recent activity event into shared focus." : entry.detail
            )
            await loadOpsStudio()
            opsMessage = "Shared focus now points at \(target)."
        } catch {
            opsMessage = "Unable to promote activity focus: \(error.localizedDescription)"
        }
    }

    private func opsBadge(title: String, detail: String, tint: Color) -> some View {
        VStack(alignment: .trailing, spacing: 4) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(tint)
            Text(detail)
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.6))
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(.white.opacity(0.05), in: Capsule())
    }

    private func actionCapsule(title: String, icon: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                Text(title)
                    .font(.caption.weight(.semibold))
            }
            .foregroundStyle(.white)
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(.white.opacity(0.06), in: Capsule())
        }
        .buttonStyle(.plain)
    }

    private func opsMetricPill(label: String, value: Int) -> some View {
        VStack(alignment: .trailing, spacing: 2) {
            Text("\(value)")
                .font(.caption.weight(.bold))
                .foregroundStyle(.white)
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(.white.opacity(0.05), in: Capsule())
    }

    private func opsEmptyCard(_ text: String) -> some View {
        Text(text)
            .font(.caption)
            .foregroundStyle(.secondary)
            .padding(10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.white.opacity(0.035), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func opsApprovalRow(_ approval: CatalystApprovalEntry) -> some View {
        HStack(alignment: .top, spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(approval.title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white)
                Text("\(approval.agent) · \(approval.risk.capitalized) risk")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                if !approval.detail.isEmpty {
                    Text(approval.detail)
                        .font(.caption2)
                        .foregroundStyle(.secondary.opacity(0.9))
                }
            }
            Spacer()
            Button {
                Task { await approveCatalystApproval(approval) }
            } label: {
                Text("Approve")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 8)
                    .background(approvalTint(for: approval.risk), in: Capsule())
            }
            .buttonStyle(.plain)
            .disabled(actionInFlight != nil)
            .opacity(actionInFlight != nil ? 0.7 : 1.0)
        }
        .padding(10)
        .background(.white.opacity(0.035), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func approvalTint(for risk: String) -> Color {
        switch risk.lowercased() {
        case "high", "critical":
            return .red.opacity(0.75)
        case "medium":
            return .orange.opacity(0.75)
        default:
            return blue.opacity(0.85)
        }
    }

    private func opsRecoveryRow(_ entry: CatalystRecoveryCaseEntry) -> some View {
        HStack(alignment: .top, spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(entry.title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white)
                Text("\(entry.statusLabel) · \(entry.executionCount)x loop · \(entry.remediationStatusLabel) · \(entry.remediationCount)x remediation")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Text("\(entry.remediationPlanStatusLabel) healing plan · \(entry.remediationPlanCompletedCount)/\(entry.remediationPlanCount) step(s)")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                if !entry.nextPlanStepLabel.isEmpty {
                    Text("Next: \(entry.nextPlanStepLabel)")
                        .font(.caption2)
                        .foregroundStyle(.cyan.opacity(0.82))
                }
                Text(entry.detail)
                    .font(.caption2)
                    .foregroundStyle(.secondary.opacity(0.9))
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 8) {
                Button {
                    Task { await executeCatalystRecovery(entry) }
                } label: {
                    Text(entry.nextActionLabel)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                        .background(.pink.opacity(0.75), in: Capsule())
                }
                .buttonStyle(.plain)
                .disabled(actionInFlight != nil)
                .opacity(actionInFlight != nil ? 0.7 : 1.0)

                Button {
                    Task { await remediateCatalystRecovery(entry) }
                } label: {
                    Text(entry.remediationActionLabel)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                        .background(Color(red: 0.45, green: 0.83, blue: 0.75).opacity(0.78), in: Capsule())
                }
                .buttonStyle(.plain)
                .disabled(actionInFlight != nil)
                .opacity(actionInFlight != nil ? 0.7 : 1.0)

                Button {
                    Task { await advanceCatalystRecoveryPlan(entry) }
                } label: {
                    Text(entry.planActionLabel)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                        .background(Color(red: 0.36, green: 0.65, blue: 0.97).opacity(0.78), in: Capsule())
                }
                .buttonStyle(.plain)
                .disabled(actionInFlight != nil || entry.remediationPlanCount <= 0 || entry.remediationPlanStatus == "completed")
                .opacity(actionInFlight != nil || entry.remediationPlanCount <= 0 || entry.remediationPlanStatus == "completed" ? 0.7 : 1.0)
            }
        }
        .padding(10)
        .background(.white.opacity(0.035), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func opsAgentRow(_ agent: CatalystAgentOpsEntry) -> some View {
        HStack(alignment: .top, spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(agent.name)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white)
                Text("\(agent.status.capitalized) · \(agent.assignment)")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Text(agent.purpose)
                    .font(.caption2)
                    .foregroundStyle(.secondary.opacity(0.9))
                Text(agent.attentionReason.isEmpty ? "Last activity: \(agent.lastActivity)" : agent.attentionReason)
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.7))
            }
            Spacer()
            Button {
                Task { await queueCatalystAgentRun(agent) }
            } label: {
                Text(agent.queueActionLabel)
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 8)
                    .background(Color(red: 0.44, green: 0.72, blue: 1.0).opacity(0.8), in: Capsule())
            }
            .buttonStyle(.plain)
            .disabled(actionInFlight != nil)
            .opacity(actionInFlight != nil ? 0.7 : 1.0)
        }
        .padding(10)
        .background(.white.opacity(0.035), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func opsSupervisionRow(_ item: CatalystSupervisionEntry) -> some View {
        HStack(alignment: .top, spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(item.title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white)
                Text("\(item.agent) · \(item.risk.capitalized) risk")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Text(item.detail)
                    .font(.caption2)
                    .foregroundStyle(.secondary.opacity(0.9))
            }
            Spacer()
            HStack(spacing: 8) {
                Button {
                    Task { await resolveCatalystSupervision(item, action: "approve") }
                } label: {
                    Text(item.approveLabel)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                        .background(Color(red: 0.7, green: 0.6, blue: 1.0).opacity(0.85), in: Capsule())
                }
                .buttonStyle(.plain)
                .disabled(actionInFlight != nil)
                .opacity(actionInFlight != nil ? 0.7 : 1.0)

                Button {
                    Task { await resolveCatalystSupervision(item, action: "reject") }
                } label: {
                    Text(item.rejectLabel)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                        .background(.white.opacity(0.14), in: Capsule())
                }
                .buttonStyle(.plain)
                .disabled(actionInFlight != nil)
                .opacity(actionInFlight != nil ? 0.7 : 1.0)
            }
        }
        .padding(10)
        .background(.white.opacity(0.035), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func opsMissionRow(_ mission: CatalystMissionEntry) -> some View {
        HStack(alignment: .top, spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(mission.title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white)
                Text("\(mission.lane.capitalized) · \(mission.status)")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Text(mission.brief)
                    .font(.caption2)
                    .foregroundStyle(.secondary.opacity(0.9))
                Text("Next: \(mission.nextStep)")
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.7))
            }
            Spacer()
            Button {
                Task {
                    if mission.lane == "now" || mission.status.lowercased() == "active" {
                        await updateCatalystMission(
                            mission,
                            status: "completed",
                            note: "Catalyst marked the mission complete from the native ops studio."
                        )
                    } else {
                        await updateCatalystMission(
                            mission,
                            status: "active",
                            note: "Catalyst moved the mission into the now lane from the native ops studio."
                        )
                    }
                }
            } label: {
                Text(mission.lane == "now" || mission.status.lowercased() == "active" ? "Complete" : "Move to Now")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 8)
                    .background(.orange.opacity(0.78), in: Capsule())
            }
            .buttonStyle(.plain)
            .disabled(actionInFlight != nil)
            .opacity(actionInFlight != nil ? 0.7 : 1.0)
        }
        .padding(10)
        .background(.white.opacity(0.035), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func moduleName(for entry: CatalystOpsActivityEntry) -> String {
        let route = entry.relatedRoute.lowercased()
        let kind = entry.relatedKind.lowercased()
        if route == "/approval-queue" || kind.contains("approval") { return "Approval Queue" }
        if route == "/recovery-center" || kind.contains("recovery") || kind.contains("failure") { return "Recovery" }
        if route == "/mission-board" || kind.contains("mission") { return "Mission Board" }
        if route == "/agent-ops-center" || kind.contains("agent") { return "Agent Ops" }
        if route == "/briefing-center" || kind.contains("brief") { return "Daily Brief" }
        if route == "/chronicle-center" || kind.contains("chronicle") { return "Chronicle" }
        if route == "/health-center" || kind.contains("health") { return "Health" }
        if route == "/navigation-center" || kind.contains("navigation") || kind.contains("route") { return "Navigation" }
        if route == "/publish" || kind.contains("publish") { return "Publish" }
        if route == "/settings-center" || kind.contains("settings") { return "Settings" }
        if route == "/huddle-center" || kind.contains("huddle") { return "Huddle" }
        if route == "/supervision-snapshot" || kind.contains("supervision") { return "Supervision" }
        if route == "/progress-center" || kind.contains("progress") { return "Progress" }
        if route == "/activity-center" || kind.contains("activity") { return "Activity Feed" }
        return "Command Center"
    }
}

private enum CatalystOpsModule: String, CaseIterable, Identifiable {
    case commandCenter
    case agentOps
    case missionBoard
    case activityFeed
    case progress
    case recovery
    case approvalQueue
    case supervision

    var id: String { rawValue }

    var title: String {
        switch self {
        case .commandCenter: return "Command Center"
        case .agentOps: return "Agent Ops"
        case .missionBoard: return "Mission Board"
        case .activityFeed: return "Activity Feed"
        case .progress: return "Progress"
        case .recovery: return "Recovery"
        case .approvalQueue: return "Approval Queue"
        case .supervision: return "Supervision"
        }
    }

    var icon: String {
        switch self {
        case .commandCenter: return "square.grid.2x2.fill"
        case .agentOps: return "person.2.badge.gearshape.fill"
        case .missionBoard: return "flag.checkered.2.crossed"
        case .activityFeed: return "bolt.horizontal.circle.fill"
        case .progress: return "chart.line.uptrend.xyaxis"
        case .recovery: return "cross.case.fill"
        case .approvalQueue: return "checklist.checked"
        case .supervision: return "eye.fill"
        }
    }

    var tint: Color {
        switch self {
        case .commandCenter: return .cyan
        case .agentOps: return Color(red: 0.44, green: 0.72, blue: 1.0)
        case .missionBoard: return .orange
        case .activityFeed: return .yellow
        case .progress: return .green
        case .recovery: return .pink
        case .approvalQueue: return Color(red: 0.9, green: 0.76, blue: 0.3)
        case .supervision: return Color(red: 0.7, green: 0.6, blue: 1.0)
        }
    }

    var routePath: String {
        switch self {
        case .commandCenter: return "/command-center"
        case .agentOps: return "/agent-ops-center"
        case .missionBoard: return "/mission-board"
        case .activityFeed: return "/activity-center"
        case .progress: return "/progress-center"
        case .recovery: return "/recovery-center"
        case .approvalQueue: return "/approval-queue"
        case .supervision: return "/supervision-snapshot"
        }
    }

    var storyNumber: String {
        switch self {
        case .commandCenter: return "1"
        case .agentOps: return "2"
        case .missionBoard: return "3"
        case .activityFeed: return "4"
        case .progress: return "5"
        case .recovery: return "6"
        case .approvalQueue: return "7"
        case .supervision: return "8"
        }
    }

    var phoneSummary: String {
        switch self {
        case .commandCenter: return "Global command shell with cross-module posture and seams."
        case .agentOps: return "Queue runs, inspect agents, and stay inside live continuity."
        case .missionBoard: return "See active missions, blockers, and board pressure on-device."
        case .activityFeed: return "Promote live operator events into shared progress focus."
        case .progress: return "Track and mutate the next shared Level 3 focus."
        case .recovery: return "Execute and inspect durable recovery cases and loops."
        case .approvalQueue: return "Approve, reject, and monitor the real queue from phone."
        case .supervision: return "Review bounded autonomy and execution posture in one lane."
        }
    }

    func badgeText(overview: CatalystOverview) -> String {
        switch self {
        case .commandCenter:
            return overview.liveWorkspace.live ? "live" : "local"
        case .agentOps:
            return "\(overview.activeWork.count) active"
        case .missionBoard:
            return "\(overview.portfolio.summaryCounts["missions"] ?? 0) tracked"
        case .activityFeed:
            return "\(overview.signals.count) signals"
        case .progress:
            return "\(overview.workflowCounts["tasks"] ?? overview.liveWorkspace.tasksCount) tasks"
        case .recovery:
            return overview.signals.isEmpty ? "watch" : "ready"
        case .approvalQueue:
            return "\(overview.latestRuns.count) recent"
        case .supervision:
            return "\(overview.connectors.count) linked"
        }
    }

    var url: URL {
        let base = JARVISEnvironment.baseURL
        return base.appending(path: routePath.trimmingCharacters(in: CharacterSet(charactersIn: "/")))
    }
}

private struct OpsModuleRouteSheet: View {
    let module: CatalystOpsModule
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            SafariRouteView(url: module.url)
                .ignoresSafeArea(edges: .bottom)
                .navigationTitle(module.title)
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .topBarLeading) {
                        Button("Close") {
                            dismiss()
                        }
                    }
                }
                .safeAreaInset(edge: .top, spacing: 0) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(module.phoneSummary)
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.72))
                        Text(module.url.absoluteString)
                            .font(.caption2.monospaced())
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(.ultraThinMaterial)
                }
        }
    }
}

private struct SafariRouteView: UIViewControllerRepresentable {
    let url: URL

    func makeUIViewController(context: Context) -> SFSafariViewController {
        let controller = SFSafariViewController(url: url)
        controller.dismissButtonStyle = .close
        return controller
    }

    func updateUIViewController(_ controller: SFSafariViewController, context: Context) {}
}

// MARK: - Section wrapper

private struct CatSection<Content: View>: View {
    let title: String
    let icon: String
    let accent: Color
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 11, weight: .semibold)).foregroundStyle(accent)
                Text(title.uppercased())
                    .font(.system(size: 10, weight: .bold)).tracking(1.0).foregroundStyle(accent.opacity(0.85))
            }
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Work item row

private struct WorkItemRow: View {
    let item: WorkLifecycleItem
    let accent: Color

    var stageColor: Color {
        let s = item.stage.lowercased()
        if s.contains("review")  { return .orange }
        if s.contains("done")    { return .green }
        if s.contains("block")   { return .red }
        return accent
    }

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            // Stage pill
            Text(item.stage.prefix(10))
                .font(.system(size: 8, weight: .bold))
                .tracking(0.5)
                .foregroundStyle(stageColor)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(stageColor.opacity(0.12), in: Capsule())

            VStack(alignment: .leading, spacing: 2) {
                Text(item.title)
                    .font(.subheadline).foregroundStyle(.white)
                HStack(spacing: 6) {
                    if !item.domain.isEmpty {
                        Text(item.domain)
                            .font(.caption2).foregroundStyle(.secondary)
                    }
                    if !item.lane.isEmpty {
                        Text("·").font(.caption2).foregroundStyle(.secondary)
                        Text(item.lane.replacingOccurrences(of: "-", with: " "))
                            .font(.caption2).foregroundStyle(.secondary)
                    }
                    if !item.updated.isEmpty {
                        Text("·").font(.caption2).foregroundStyle(.secondary)
                        Text(relativeDate(item.updated))
                            .font(.caption2).foregroundStyle(.secondary)
                    }
                }
            }
        }
        .padding(.vertical, 2)
    }

    private func relativeDate(_ iso: String) -> String {
        let f = ISO8601DateFormatter()
        guard let d = f.date(from: iso) else { return iso.prefix(10).description }
        return d.formatted(.relative(presentation: .named))
    }
}

private struct LaneRow: View {
    let lane: CatalystLane

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(lane.label)
                    .font(.subheadline)
                    .foregroundStyle(.white)
                Spacer()
                if !lane.status.isEmpty {
                    Text(lane.status)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.secondary)
                }
            }
            if !lane.description.isEmpty {
                Text(lane.description)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }
}

// MARK: - Signal row

private struct SignalRow: View {
    let signal: CatalystSignal

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(signal.title).font(.subheadline).foregroundStyle(.white)
                Spacer()
                Text(signal.source).font(.caption2).foregroundStyle(.secondary)
            }
            if !signal.tags.isEmpty {
                HStack(spacing: 4) {
                    ForEach(signal.tags.prefix(3), id: \.self) { tag in
                        Text("#\(tag)")
                            .font(.system(size: 8, weight: .medium))
                            .foregroundStyle(Color(red: 0.25, green: 0.55, blue: 1.0).opacity(0.8))
                            .padding(.horizontal, 5).padding(.vertical, 2)
                            .background(Color(red: 0.25, green: 0.55, blue: 1.0).opacity(0.1), in: Capsule())
                    }
                }
            }
        }
        .padding(.vertical, 2)
    }
}

private struct ConnectorRow: View {
    let connector: CatalystConnector

    private var statusColor: Color {
        switch connector.status.lowercased() {
        case "connected", "local", "active", "ready":
            return .green
        case "planned":
            return .orange
        default:
            return .secondary
        }
    }

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Circle()
                .fill(statusColor.opacity(0.85))
                .frame(width: 8, height: 8)
                .padding(.top, 6)
            VStack(alignment: .leading, spacing: 3) {
                HStack {
                    Text(connector.label)
                        .font(.subheadline)
                        .foregroundStyle(.white)
                    Spacer()
                    Text(connector.status)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(statusColor)
                }
                if !connector.notes.isEmpty {
                    Text(connector.notes)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(.vertical, 2)
    }
}

private struct RunRow: View {
    let run: CatalystRunSummary

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack {
                Text(run.label)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(Color(red: 0.25, green: 0.55, blue: 1.0).opacity(0.85))
                Spacer()
                if !run.timestamp.isEmpty {
                    Text(relativeDate(run.timestamp))
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
            Text(run.title)
                .font(.subheadline)
                .foregroundStyle(.white)
        }
        .padding(.vertical, 2)
    }

    private func relativeDate(_ iso: String) -> String {
        let f = ISO8601DateFormatter()
        guard let d = f.date(from: iso) else { return iso.prefix(10).description }
        return d.formatted(.relative(presentation: .named))
    }
}

// MARK: - Portfolio tile

private struct PortfolioTile: View {
    let label: String
    let count: Int
    let accent: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("\(count)")
                .font(.system(size: 26, weight: .bold).monospacedDigit())
                .foregroundStyle(.white)
            Text(label)
                .font(.caption2).foregroundStyle(.secondary).lineLimit(2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .glassEffect(in: RoundedRectangle(cornerRadius: 12))
    }
}

#Preview { CatalystView() }
