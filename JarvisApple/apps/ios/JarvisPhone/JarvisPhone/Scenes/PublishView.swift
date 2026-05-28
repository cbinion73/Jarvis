import SwiftUI
import JarvisKit

// MARK: - PublishView  "The Press Room"
// Robbie Robertson · Publishing & Revenue

struct PublishView: View {

    @State private var overview: PublishOverview?
    @State private var isLoading  = false
    @State private var error: String?

    private let green = Color(red: 0.15, green: 0.85, blue: 0.45)

    var body: some View {
        NavigationStack {
            ZStack {
                ZStack {
                    Color.black
                    LinearGradient(
                        colors: [Color(red: 0.01, green: 0.07, blue: 0.03), Color.black],
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
            .navigationTitle("Publish")
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
            Image(systemName: "doc.richtext.fill")
                .font(.system(size: 36)).foregroundStyle(green.opacity(0.4))
                .symbolEffect(.pulse)
            Text("Loading publishing data…").font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Content

    @ViewBuilder
    private func contentView(_ ov: PublishOverview) -> some View {
        ScrollView {
            VStack(spacing: 14) {

                // ── Revenue banner ────────────────────────────────
                revenueBanner(ov.revenueSummary)

                // ── Projects ──────────────────────────────────────
                if !ov.projects.isEmpty {
                    PressSection(title: "Projects", icon: "doc.text.fill", accent: green) {
                        ForEach(ov.projects) { proj in
                            ProjectRow(project: proj, green: green)
                            if proj.id != ov.projects.last?.id { Divider().opacity(0.2) }
                        }
                    }
                }

                // ── Revenue streams ───────────────────────────────
                if !ov.revenueSummary.streams.isEmpty {
                    PressSection(title: "Revenue Streams", icon: "dollarsign.circle.fill", accent: green) {
                        ForEach(ov.revenueSummary.streams) { stream in
                            StreamRow(stream: stream, green: green)
                            if stream.id != ov.revenueSummary.streams.last?.id { Divider().opacity(0.2) }
                        }
                    }
                }

                // ── Upcoming calendar ─────────────────────────────
                if !ov.upcoming.isEmpty {
                    PressSection(title: "Upcoming Content", icon: "calendar.badge.plus", accent: green) {
                        ForEach(ov.upcoming) { item in
                            CalendarRow(item: item)
                            if item.id != ov.upcoming.last?.id { Divider().opacity(0.2) }
                        }
                    }
                }
            }
            .padding(.horizontal, 16).padding(.vertical, 12)
        }
    }

    // MARK: - Revenue banner

    @ViewBuilder
    private func revenueBanner(_ rev: RevenueSummary) -> some View {
        HStack(spacing: 14) {
            VStack(alignment: .leading, spacing: 4) {
                Text("MONTHLY ESTIMATE")
                    .font(.system(size: 9, weight: .bold)).tracking(1.2).foregroundStyle(.secondary)
                Text(rev.monthlyEstimate.formatted(.currency(code: "USD")))
                    .font(.system(size: 32, weight: .bold).monospacedDigit())
                    .foregroundStyle(rev.monthlyEstimate > 0 ? green : .white.opacity(0.3))
                Text("\(rev.streamCount) active stream\(rev.streamCount == 1 ? "" : "s")")
                    .font(.caption2).foregroundStyle(.secondary)
            }
            Spacer()
            ZStack {
                Circle().fill(green.opacity(0.1)).frame(width: 56, height: 56)
                Image(systemName: "arrow.up.right")
                    .font(.system(size: 22, weight: .bold))
                    .foregroundStyle(rev.monthlyEstimate > 0 ? green : .white.opacity(0.2))
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(green.opacity(0.15), lineWidth: 1))
    }

    // MARK: - Error

    private func errorView(_ msg: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "doc.richtext.fill").font(.system(size: 44)).foregroundStyle(green.opacity(0.4))
            Text("Publishing unavailable").font(.headline).foregroundStyle(.white)
            Text(msg).font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
            Button("Retry") { Task { await load() } }
                .buttonStyle(.borderedProminent).tint(green)
        }
        .padding(24).glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32).frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func load() async {
        isLoading = true; error = nil
        do { overview = try await AppleAPIClient.shared.fetchPublishing() }
        catch { self.error = error.localizedDescription }
        isLoading = false
    }
}

// MARK: - Press section

private struct PressSection<Content: View>: View {
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

// MARK: - Project row

private struct ProjectRow: View {
    let project: PublishProject
    let green: Color

    var statusColor: Color {
        switch project.status {
        case "published": return green
        case "ready":     return .cyan
        case "editing":   return .orange
        default:          return .white.opacity(0.4)
        }
    }

    var typeIcon: String {
        switch project.type {
        case "book":   return "book.closed.fill"
        case "course": return "graduationcap.fill"
        default:       return "doc.text.fill"
        }
    }

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: typeIcon)
                .font(.system(size: 16))
                .foregroundStyle(green.opacity(0.6))
                .frame(width: 22)

            VStack(alignment: .leading, spacing: 2) {
                Text(project.title).font(.subheadline).foregroundStyle(.white)
                HStack(spacing: 4) {
                    Text(project.platform).font(.caption2).foregroundStyle(.secondary)
                    if !project.platform.isEmpty && !project.status.isEmpty {
                        Text("·").font(.caption2).foregroundStyle(.secondary)
                    }
                }
            }
            Spacer()
            Text(project.status.capitalized)
                .font(.system(size: 9, weight: .bold))
                .foregroundStyle(statusColor)
                .padding(.horizontal, 7).padding(.vertical, 3)
                .background(statusColor.opacity(0.12), in: Capsule())
        }
        .padding(.vertical, 2)
    }
}

// MARK: - Stream row

private struct StreamRow: View {
    let stream: RevenueStream
    let green: Color

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(stream.source).font(.subheadline).foregroundStyle(.white)
                Text(stream.type.replacingOccurrences(of: "_", with: " ").capitalized)
                    .font(.caption2).foregroundStyle(.secondary)
            }
            Spacer()
            Text(stream.monthlyEst.formatted(.currency(code: "USD")))
                .font(.subheadline.bold().monospacedDigit())
                .foregroundStyle(stream.monthlyEst > 0 ? green : .secondary)
            Text("/ mo")
                .font(.caption2).foregroundStyle(.secondary)
        }
        .padding(.vertical, 2)
    }
}

// MARK: - Calendar row

private struct CalendarRow: View {
    let item: CalendarItem

    var statusColor: Color {
        switch item.status {
        case "ready":   return .cyan
        case "draft":   return .orange
        case "outline": return .yellow
        default:        return .white.opacity(0.3)
        }
    }

    var body: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(item.title).font(.subheadline).foregroundStyle(.white)
                HStack(spacing: 4) {
                    if !item.contentType.isEmpty {
                        Text(item.contentType.replacingOccurrences(of: "_", with: " ").capitalized)
                            .font(.caption2).foregroundStyle(.secondary)
                    }
                    if !item.platform.isEmpty {
                        Text("·").font(.caption2).foregroundStyle(.secondary)
                        Text(item.platform).font(.caption2).foregroundStyle(.secondary)
                    }
                }
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text(item.plannedDate.prefix(10))
                    .font(.caption2.monospacedDigit()).foregroundStyle(.secondary)
                Text(item.status.capitalized)
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(statusColor)
            }
        }
        .padding(.vertical, 2)
    }
}

#Preview { PublishView() }
