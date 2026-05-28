import SwiftUI
import JarvisKit

// MARK: - CatalystView  "The Workshop"
// Mantis · Personal Workflow Intelligence

struct CatalystView: View {

    @State private var overview: CatalystOverview?
    @State private var isLoading  = false
    @State private var error: String?

    private let blue = Color(red: 0.25, green: 0.55, blue: 1.0)

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

                // ── Active work ───────────────────────────────────
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

                // ── Signals ───────────────────────────────────────
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

                // ── Portfolio summary ─────────────────────────────
                if !ov.portfolio.isEmpty {
                    CatSection(title: "Portfolio", icon: "chart.bar.xaxis", accent: blue) {
                        LazyVGrid(
                            columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 2),
                            spacing: 10
                        ) {
                            ForEach(ov.portfolio.sorted(by: { $0.key < $1.key }), id: \.key) { key, val in
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
