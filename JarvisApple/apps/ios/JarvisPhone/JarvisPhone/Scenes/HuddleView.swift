import SwiftUI
import JarvisKit

// MARK: - HuddleView  "The Situation Room"
// All agents · Daily standup

struct HuddleView: View {

    @State private var overview: HuddleOverview?
    @State private var isLoading  = false
    @State private var error: String?

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
                    SituationStat(label: "Blockers", value: "\(ov.blockers.count)",
                                  accent: ov.blockers.isEmpty ? .green : .red)
                    SituationStat(label: "Highlights", value: "\(ov.highlights.count)", accent: teal.opacity(0.7))
                }
                .padding(14)
                .glassEffect(in: RoundedRectangle(cornerRadius: 14))

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
                Spacer()
                Text(report.status.capitalized)
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(statusColor)
                    .padding(.horizontal, 6).padding(.vertical, 2)
                    .background(statusColor.opacity(0.12), in: Capsule())
            }
            if !report.summary.isEmpty {
                Text(report.summary)
                    .font(.caption).foregroundStyle(.white.opacity(0.7))
                    .lineLimit(2)
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
}

#Preview { HuddleView() }
