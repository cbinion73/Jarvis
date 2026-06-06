import SwiftUI
import JarvisKit
import SafariServices

// MARK: - CatalystView  "The Workshop"
// Mantis · Personal Workflow Intelligence

struct CatalystView: View {

    @State private var overview: CatalystOverview?
    @State private var isLoading  = false
    @State private var error: String?
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
                    Text("JARVIS Ops Deck")
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                        .foregroundStyle(.white)
                    Text("Mission pressure, approvals, recovery, continuity, and supervision are now reachable on iPhone through the real hosted product.")
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
                        title: "\(opsModules.count) Modules",
                        detail: "Operational routes ready",
                        tint: blue
                    )
                }
            }

            HStack(spacing: 10) {
                actionCapsule(title: "Command Center", icon: "square.grid.2x2.fill") {
                    selectedModule = .commandCenter
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
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 10) {
                ForEach(opsModules.prefix(8)) { module in
                    VStack(alignment: .leading, spacing: 8) {
                        HStack(spacing: 8) {
                            Text(module.storyNumber)
                                .font(.caption2.weight(.bold))
                                .foregroundStyle(module.tint)
                                .frame(width: 24, height: 24)
                                .background(module.tint.opacity(0.14), in: Circle())
                            Text(module.title)
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.white)
                        }
                        Text(module.phoneSummary)
                            .font(.caption2)
                            .foregroundStyle(.white.opacity(0.62))
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .frame(width: 172, alignment: .leading)
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
        } catch {
            self.error = error.localizedDescription
        }
        isLoading = false
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
