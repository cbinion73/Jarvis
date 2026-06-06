import SwiftUI
import JarvisKit

// MARK: - HuddleView  "The Situation Room"
// All agents · Daily standup

struct HuddleView: View {

    @State private var overview: HuddleOverview?
    @State private var isLoading  = false
    @State private var error: String?
    @State private var isStartingPartyMode = false
    @State private var partyModeMessage = ""

    private let teal = Color(red: 0.15, green: 0.75, blue: 0.75)

    var body: some View {
        NavigationStack {
            ZStack {
                ZStack {
                    Color.black
                    LinearGradient(
                        colors: [Color(red: 0.01, green: 0.07, blue: 0.07), Color.black],
                        startPoint: .top, endPoint: UnitPoint(x: 0.5, y: 0.5)
                    )
                }
                .ignoresSafeArea()

                Group {
                    if isLoading && overview == nil { loadingView }
                    else if let ov = overview { contentView(ov) }
                    else if let e = error { errorView(e) }
                    else { loadingView }
                }
            }
            .navigationTitle("Huddle")
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
    }

    // MARK: - Loading

    private var loadingView: some View {
        VStack(spacing: 16) {
            Image(systemName: "person.3.fill")
                .font(.system(size: 36)).foregroundStyle(teal.opacity(0.4))
                .symbolEffect(.pulse)
            Text("Collecting agent standups…").font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Content

    @ViewBuilder
    private func contentView(_ ov: HuddleOverview) -> some View {
        ScrollView {
            VStack(spacing: 14) {

                // ── Summary strip ─────────────────────────────────
                HStack(spacing: 14) {
                    SituationStat(label: "Agents", value: "\(ov.reports.count)", accent: teal)
                    SituationStat(label: "Active Work", value: "\(ov.totalActiveWork)", accent: teal.opacity(0.85))
                    SituationStat(label: "Blockers", value: "\(ov.blockers.count)",
                                  accent: ov.blockers.isEmpty ? .green : .red)
                    SituationStat(label: "Approvals", value: "\(ov.approvalsCount)",
                                  accent: ov.approvalsCount == 0 ? teal.opacity(0.7) : .orange)
                }
                .padding(14)
                .glassEffect(in: RoundedRectangle(cornerRadius: 14))

                if let continuity = ov.continuity {
                    continuitySection(continuity)
                }

                if let runtime = ov.runtime {
                    runtimeSection(runtime)
                }

                if let partyMode = ov.partyMode {
                    partyModeSection(partyMode, dossiers: ov.dossiers)
                }

                if !ov.approvals.isEmpty {
                    HuddleSection(title: "Awaiting Approval", icon: "checklist.checked", accent: .orange) {
                        ForEach(ov.approvals) { approval in
                            ApprovalRow(approval: approval)
                            if approval.id != ov.approvals.last?.id { Divider().opacity(0.2) }
                        }
                    }
                }

                // ── Active blockers ───────────────────────────────
                if !ov.blockers.isEmpty {
                    HuddleSection(title: "Blockers", icon: "exclamationmark.octagon.fill", accent: .red) {
                        ForEach(Array(ov.blockers.enumerated()), id: \.offset) { _, b in
                            HStack(alignment: .top, spacing: 8) {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundStyle(.red).font(.caption).padding(.top, 2)
                                Text(b).font(.subheadline).foregroundStyle(.white)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                }

                // ── Highlights ────────────────────────────────────
                if !ov.highlights.isEmpty {
                    HuddleSection(title: "Highlights", icon: "star.fill", accent: .yellow) {
                        ForEach(Array(ov.highlights.enumerated()), id: \.offset) { _, h in
                            HStack(alignment: .top, spacing: 8) {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(.green).font(.caption).padding(.top, 2)
                                Text(h).font(.subheadline).foregroundStyle(.white)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                }

                // ── Agent reports ─────────────────────────────────
                if !ov.reports.isEmpty {
                    HuddleSection(title: "Agent Status", icon: "person.3.sequence.fill", accent: teal) {
                        ForEach(ov.reports) { report in
                            AgentReportRow(report: report, teal: teal)
                            if report.id != ov.reports.last?.id { Divider().opacity(0.2) }
                        }
                    }
                } else {
                    VStack(spacing: 10) {
                        Image(systemName: "person.3.fill")
                            .font(.system(size: 40)).foregroundStyle(teal.opacity(0.25))
                        Text("No agent reports available yet")
                            .font(.subheadline).foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity).padding(32)
                    .glassEffect(in: RoundedRectangle(cornerRadius: 16))
                }
            }
            .padding(.horizontal, 16).padding(.vertical, 12)
        }
    }

    // MARK: - Error

    private func errorView(_ msg: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "person.3.fill").font(.system(size: 44)).foregroundStyle(teal.opacity(0.4))
            Text("Huddle unavailable").font(.headline).foregroundStyle(.white)
            Text(msg).font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
            Button("Retry") { Task { await load() } }
                .buttonStyle(.borderedProminent).tint(teal)
        }
        .padding(24).glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32).frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func load() async {
        isLoading = true; error = nil
        do { overview = try await AppleAPIClient.shared.fetchHuddle() }
        catch { self.error = error.localizedDescription }
        isLoading = false
    }

    @ViewBuilder
    private func runtimeSection(_ runtime: HuddleRuntimeSummary) -> some View {
        HuddleSection(title: "Runtime Posture", icon: "waveform.path.ecg.rectangle.fill", accent: teal) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 10) {
                    runtimePill("\(runtime.awakeCount)", "Awake", tint: teal)
                    runtimePill("\(runtime.idleCount)", "Idle", tint: .secondary)
                    runtimePill("\(runtime.blockedCount)", "Blocked", tint: runtime.blockedCount == 0 ? .green : .red)
                }
                HStack(spacing: 8) {
                    if !runtime.activeMode.isEmpty {
                        RuntimeBadge(text: runtime.activeMode.replacingOccurrences(of: "-", with: " ").uppercased(), color: teal)
                    }
                    if runtime.quietHoursActive {
                        RuntimeBadge(text: "QUIET HOURS", color: .orange)
                    }
                    if !runtime.lastTickAt.isEmpty {
                        Text(runtime.lastTickAt.prefix(19).replacingOccurrences(of: "T", with: " "))
                            .font(.caption2.monospacedDigit())
                            .foregroundStyle(.secondary)
                    }
                }
                if !runtime.statuses.isEmpty {
                    ForEach(runtime.statuses) { status in
                        RuntimeAgentRow(status: status, accent: teal)
                        if status.id != runtime.statuses.last?.id { Divider().opacity(0.2) }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func partyModeSection(_ partyMode: HuddlePartyStatus, dossiers: [HuddleDossierSummary]) -> some View {
        HuddleSection(title: "Overnight Orchestration", icon: "moon.stars.fill", accent: .purple) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top, spacing: 12) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(partyModeTitle(partyMode.status))
                            .font(.headline)
                            .foregroundStyle(.white)
                        if !partyMode.lastLog.isEmpty {
                            Text(partyMode.lastLog)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    Spacer()
                    Button(isStartingPartyMode ? "Starting…" : partyButtonTitle(partyMode.status)) {
                        Task { await startPartyMode() }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.purple)
                    .disabled(isStartingPartyMode || partyMode.status.lowercased() == "running")
                }

                if !partyModeMessage.isEmpty {
                    Text(partyModeMessage)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                HStack(spacing: 10) {
                    runtimePill("\(partyMode.dossiersBuiltCount)", "Built", tint: .purple)
                    runtimePill("\(partyMode.itemsDreamed)", "Dreamed", tint: .cyan)
                    runtimePill("\(dossiers.count)", "Ready", tint: .green)
                }

                if !dossiers.isEmpty {
                    ForEach(dossiers) { dossier in
                        DossierRow(dossier: dossier)
                        if dossier.id != dossiers.last?.id { Divider().opacity(0.2) }
                    }
                }
            }
        }
    }

    private func startPartyMode() async {
        isStartingPartyMode = true
        partyModeMessage = ""
        do {
            let result = try await AppleAPIClient.shared.startHuddlePartyMode()
            switch result.status {
            case "started":
                partyModeMessage = "Party mode started."
            case "already_running":
                partyModeMessage = "Party mode is already running."
            case "staged_for_review":
                partyModeMessage = result.boundaryReason ?? "Party mode start was staged for review."
            case "blocked_by_boundary":
                partyModeMessage = result.boundaryReason ?? "Party mode start was blocked by governance boundaries."
            default:
                partyModeMessage = result.status.replacingOccurrences(of: "_", with: " ").capitalized
            }
            await load()
        } catch {
            self.error = error.localizedDescription
        }
        isStartingPartyMode = false
    }

    private func partyModeTitle(_ status: String) -> String {
        switch status.lowercased() {
        case "running": return "Agents Working Overnight"
        case "completed": return "Last Session Completed"
        default: return "Overnight Research Idle"
        }
    }

    private func partyButtonTitle(_ status: String) -> String {
        status.lowercased() == "completed" ? "Run Again" : "Wake Agents"
    }

    @ViewBuilder
    private func continuitySection(_ continuity: HuddleContinuity) -> some View {
        HuddleSection(title: "Carry Forward", icon: "clock.arrow.trianglehead.counterclockwise.rotate.90", accent: .cyan) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 10) {
                    runtimePill("\(continuity.profileFactCount)", "Facts", tint: .cyan)
                    runtimePill("\(continuity.readyDossierCount)", "Dossiers", tint: .purple)
                    runtimePill("\(continuity.activeDomains.count)", "Domains", tint: teal)
                }

                if !continuity.councilFocus.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("COUNCIL FOCUS")
                            .font(.system(size: 10, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.cyan.opacity(0.85))
                        Text(continuity.councilFocus)
                            .font(.subheadline)
                            .foregroundStyle(.white)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                if !continuity.activeDomains.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("ACTIVE DOMAINS")
                            .font(.system(size: 10, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.cyan.opacity(0.85))
                        Text(continuity.activeDomains.joined(separator: " • "))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                if !continuity.guidanceLines.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("COUNCIL RHYTHM")
                            .font(.system(size: 10, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.cyan.opacity(0.85))
                        ForEach(Array(continuity.guidanceLines.enumerated()), id: \.offset) { _, line in
                            Text(line)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }

                if !continuity.recentProfileFacts.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("DURABLE PATTERNS")
                            .font(.system(size: 10, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.cyan.opacity(0.85))
                        ForEach(continuity.recentProfileFacts.prefix(2)) { fact in
                            VStack(alignment: .leading, spacing: 2) {
                                Text(fact.title)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                Text(fact.summary)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                }

                if !continuity.recentFirstLight.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("RECENT FIRST LIGHT")
                            .font(.system(size: 10, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.cyan.opacity(0.85))
                        ForEach(continuity.recentFirstLight.prefix(2)) { moment in
                            VStack(alignment: .leading, spacing: 2) {
                                Text(moment.label)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                Text(moment.summary)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                }
            }
        }
    }
}

// MARK: - Summary stat tile

private struct SituationStat: View {
    let label: String
    let value: String
    let accent: Color

    var body: some View {
        VStack(spacing: 3) {
            Text(value)
                .font(.system(size: 24, weight: .bold).monospacedDigit())
                .foregroundStyle(accent)
            Text(label)
                .font(.caption2).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }
}

private struct RuntimeBadge: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(.system(size: 9, weight: .bold))
            .foregroundStyle(color)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(color.opacity(0.14), in: Capsule())
    }
}

// MARK: - Huddle section

private struct HuddleSection<Content: View>: View {
    let title: String
    let icon: String
    let accent: Color
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: icon).font(.system(size: 11, weight: .semibold)).foregroundStyle(accent)
                Text(title.uppercased()).font(.system(size: 10, weight: .bold)).tracking(1.0).foregroundStyle(accent.opacity(0.85))
            }
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

private struct RuntimeAgentRow: View {
    let status: HuddleRuntimeAgent
    let accent: Color

    private var stateColor: Color {
        switch status.state.lowercased() {
        case "awake": return accent
        case "blocked": return .red
        case "idle": return .secondary
        default: return .white.opacity(0.55)
        }
    }

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Circle()
                .fill(stateColor.opacity(0.18))
                .frame(width: 26, height: 26)
                .overlay(
                    Image(systemName: status.state.lowercased() == "blocked" ? "exclamationmark.octagon.fill" : status.state.lowercased() == "awake" ? "bolt.fill" : "moon.zzz.fill")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(stateColor)
                )
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(status.label.isEmpty ? status.agentId : status.label)
                        .font(.subheadline)
                        .foregroundStyle(.white)
                    Spacer()
                    Text(status.state.capitalized)
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(stateColor)
                }
                if !status.reason.isEmpty {
                    Text(status.reason)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                HStack(spacing: 8) {
                    if !status.nextRunAt.isEmpty {
                        Text("Next \(status.nextRunAt.prefix(16).replacingOccurrences(of: "T", with: " "))")
                            .font(.caption2.monospacedDigit())
                            .foregroundStyle(.secondary)
                    }
                    if status.dueNow {
                        Text("Due now")
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(.orange)
                    }
                }
            }
        }
        .padding(.vertical, 2)
    }
}

private struct DossierRow: View {
    let dossier: HuddleDossierSummary

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(dossier.title)
                        .font(.subheadline)
                        .foregroundStyle(.white)
                    Text(dossier.status.replacingOccurrences(of: "_", with: " ").capitalized)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.purple.opacity(0.85))
                }
                Spacer()
                if dossier.revenueEstimateHigh > 0 {
                    Text("$\(dossier.revenueEstimateLow)-$\(dossier.revenueEstimateHigh)")
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(.green)
                }
            }
            if !dossier.executiveSummary.isEmpty {
                Text(dossier.executiveSummary)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            if !dossier.firstAction.isEmpty {
                Text("First action: \(dossier.firstAction)")
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.78))
            }
        }
        .padding(.vertical, 2)
    }
}

private struct RuntimeMetricPill: View {
    let value: String
    let label: String
    let tint: Color

    var body: some View {
        VStack(spacing: 2) {
            Text(value)
                .font(.system(size: 16, weight: .bold).monospacedDigit())
                .foregroundStyle(tint)
            Text(label.uppercased())
                .font(.system(size: 8, weight: .bold))
                .tracking(0.8)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
        .background(tint.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
    }
}

private func runtimePill(_ value: String, _ label: String, tint: Color) -> some View {
    RuntimeMetricPill(value: value, label: label, tint: tint)
}

// MARK: - Agent report row

private struct AgentReportRow: View {
    let report: AgentReport
    let teal: Color

    var statusColor: Color {
        switch report.status {
        case "ok":      return .green
        case "busy":    return teal
        case "blocked": return .red
        case "idle":    return .white.opacity(0.3)
        default:        return .white.opacity(0.3)
        }
    }

    var statusIcon: String {
        switch report.status {
        case "ok":      return "checkmark.circle.fill"
        case "busy":    return "gearshape.fill"
        case "blocked": return "xmark.octagon.fill"
        default:        return "minus.circle.fill"
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Image(systemName: statusIcon)
                    .foregroundStyle(statusColor).font(.caption)
                Text(report.agentName.isEmpty ? report.agentId : report.agentName)
                    .font(.subheadline.weight(.medium)).foregroundStyle(.white)
                if !report.domain.isEmpty {
                    Text(report.domain.capitalized)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                HStack(spacing: 6) {
                    Text(report.source.uppercased())
                        .font(.system(size: 8, weight: .bold))
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 6).padding(.vertical, 3)
                        .background(Color.white.opacity(0.06), in: Capsule())
                    Text(report.status.capitalized)
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(statusColor)
                        .padding(.horizontal, 6).padding(.vertical, 2)
                        .background(statusColor.opacity(0.12), in: Capsule())
                }
            }
            if !report.summary.isEmpty {
                Text(report.summary)
                    .font(.caption).foregroundStyle(.white.opacity(0.7))
                    .lineLimit(2)
            }
            if !report.yesterday.isEmpty {
                detailBlock("Yesterday", text: report.yesterday)
            }
            if !report.today.isEmpty {
                detailBlock("Today", text: report.today)
            }
            if !report.needs.isEmpty {
                detailBlock("Needs", text: report.needs, accent: needsAccent)
            }
            if !report.highlights.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(report.highlights, id: \.self) { item in
                            Text(item)
                                .font(.caption2)
                                .foregroundStyle(.white.opacity(0.82))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 5)
                                .background(teal.opacity(0.12), in: Capsule())
                        }
                    }
                }
            }
            if report.activeWorkCount > 0 {
                Text("\(report.activeWorkCount) active work item\(report.activeWorkCount == 1 ? "" : "s") in pipeline")
                    .font(.caption2)
                    .foregroundStyle(teal.opacity(0.82))
            }
            if !report.blockers.isEmpty {
                ForEach(report.blockers, id: \.self) { b in
                    HStack(spacing: 4) {
                        Image(systemName: "minus.circle").foregroundStyle(.red).font(.caption2)
                        Text(b).font(.caption2).foregroundStyle(.red.opacity(0.8))
                    }
                }
            }
        }
        .padding(.vertical, 2)
    }

    private var needsAccent: Color {
        let lowered = report.needs.lowercased()
        return lowered.contains("nothing needed") || lowered.contains("running independently")
            ? .secondary
            : .orange
    }

    private func detailBlock(_ label: String, text: String, accent: Color = .secondary) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label.uppercased())
                .font(.system(size: 9, weight: .bold))
                .tracking(0.9)
                .foregroundStyle(accent.opacity(0.85))
            Text(text)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.78))
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

private struct ApprovalRow: View {
    let approval: HuddleApproval

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(approval.title)
                        .font(.subheadline.bold())
                        .foregroundStyle(.white)
                    HStack(spacing: 4) {
                        if !approval.agent.isEmpty {
                            Text(approval.agent)
                        }
                        if !approval.domain.isEmpty {
                            if !approval.agent.isEmpty { Text("·") }
                            Text(approval.domain)
                        }
                    }
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                }
                Spacer()
                Text("Review")
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(.orange)
                    .padding(.horizontal, 7)
                    .padding(.vertical, 3)
                    .background(Color.orange.opacity(0.12), in: Capsule())
            }

            if !approval.proposal.isEmpty {
                Text(approval.proposal)
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.8))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

#Preview { HuddleView() }
