import SwiftUI
import JarvisKit

// MARK: - ChronicleView  "The Journal"
// Disciple · Chronicle & Reflection

struct ChronicleView: View {

    @State private var overview: ChronicleOverview?
    @State private var isLoading  = false
    @State private var error: String?
    @State private var capturing  = false
    @State private var captureType = "reflection"
    @State private var captureText = ""
    @FocusState private var captureFieldFocused: Bool

    private let amber = Color(red: 0.9, green: 0.65, blue: 0.25)

    var body: some View {
        NavigationStack {
            ZStack {
                ZStack {
                    Color.black
                    LinearGradient(
                        colors: [Color(red: 0.07, green: 0.05, blue: 0.01), Color.black],
                        startPoint: .top, endPoint: UnitPoint(x: 0.5, y: 0.5)
                    )
                }
                .ignoresSafeArea()

                VStack(spacing: 0) {
                    Group {
                        if isLoading && overview == nil {
                            loadingView
                        } else if let ov = overview {
                            entriesList(ov)
                        } else if let e = error {
                            errorView(e)
                        }
                    }

                    if capturing { captureRow }
                }
            }
            .navigationTitle("Chronicle")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button { Task { await load() } } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .glassEffect(in: Circle())
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        capturing.toggle()
                        if capturing { captureFieldFocused = true }
                    } label: {
                        Image(systemName: capturing ? "xmark.circle.fill" : "plus.circle.fill")
                            .foregroundStyle(capturing ? .secondary : amber)
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
            Image(systemName: "book.fill")
                .font(.system(size: 36)).foregroundStyle(amber.opacity(0.4))
                .symbolEffect(.pulse)
            Text("Loading entries…").font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Entries list

    @ViewBuilder
    private func entriesList(_ ov: ChronicleOverview) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                if let context = ov.context {
                    contextSection(context)
                }

                if let patterns = ov.patterns {
                    patternsSection(patterns)
                }

                if ov.entries.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "book.pages")
                            .font(.system(size: 48)).foregroundStyle(amber.opacity(0.3))
                        Text("No entries yet")
                            .font(.title3.bold()).foregroundStyle(.white)
                        Text("Tap + to capture your first reflection, prayer, or note.")
                            .font(.subheadline).foregroundStyle(.secondary).multilineTextAlignment(.center)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(32)
                    .glassEffect(in: RoundedRectangle(cornerRadius: 20))
                } else {
                    sectionHeader("Recent Entries", subtitle: "\(ov.entries.count) loaded from live Chronicle")
                    ForEach(ov.entries) { entry in
                        EntryCard(entry: entry, amber: amber)
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    @ViewBuilder
    private func contextSection(_ context: ChronicleContext) -> some View {
        sectionHeader("Formation Context", subtitle: "Live Chronicle context from JARVIS")
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                contextMetric(title: "Entries", value: "\(context.totalEntries)")
                contextMetric(title: "Active Prayers", value: "\(context.activePrayerCount)")
                contextMetric(title: "Answered", value: "\(context.answeredPrayerCount)")
            }

            if let study = context.study, !study.passage.isEmpty || !study.title.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Current Study")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(amber.opacity(0.85))
                    Text(study.passage.isEmpty ? study.title : study.passage)
                        .font(.headline)
                        .foregroundStyle(.white)
                    if !study.title.isEmpty && study.title != study.passage {
                        Text(study.title)
                            .font(.subheadline)
                            .foregroundStyle(.white.opacity(0.72))
                    }
                    if !study.date.isEmpty {
                        Text(study.date)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            if let rhythm = context.todaysRhythm, !rhythm.name.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Today's Rhythm")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(amber.opacity(0.85))
                    Text(rhythm.name)
                        .font(.subheadline.bold())
                        .foregroundStyle(.white)
                    if !rhythm.description.isEmpty {
                        Text(rhythm.description)
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.72))
                    }
                }
            }

            if !context.activePrayers.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Active Prayers")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(amber.opacity(0.85))
                    ForEach(context.activePrayers.prefix(3)) { prayer in
                        HStack(alignment: .top, spacing: 8) {
                            Image(systemName: "hands.sparkles.fill")
                                .font(.caption2)
                                .foregroundStyle(.purple.opacity(0.85))
                            VStack(alignment: .leading, spacing: 2) {
                                Text(prayer.text)
                                    .font(.caption)
                                    .foregroundStyle(.white.opacity(0.84))
                                if !prayer.category.isEmpty {
                                    Text(prayer.category)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                }
            }

            if !context.topThemes.isEmpty {
                themeChipWrap(context.topThemes.map { ChronicleThemeCount(theme: $0, count: 0) }, showsCounts: false)
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 18))
    }

    @ViewBuilder
    private func patternsSection(_ patterns: ChroniclePatterns) -> some View {
        sectionHeader("Patterns", subtitle: "Live reflection and prayer trends")
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                contextMetric(title: "Streak", value: "\(patterns.writingStreakDays)d")
                contextMetric(title: "Last \(patterns.windowDays)", value: "\(patterns.totalRecentEntries)")
                contextMetric(title: "Answered", value: "\(patterns.prayerArc.answeredRecent)")
            }

            if !patterns.entryTypeBreakdown.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Entry Types")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(amber.opacity(0.85))
                    HStack(spacing: 8) {
                        ForEach(patterns.entryTypeBreakdown.sorted(by: { $0.value > $1.value }), id: \.key) { key, value in
                            VStack(spacing: 2) {
                                Text("\(value)")
                                    .font(.subheadline.bold())
                                    .foregroundStyle(.white)
                                Text(key.capitalized)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 8)
                            .background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 12))
                        }
                    }
                }
            }

            if !patterns.recurringThemes.isEmpty {
                themeChipWrap(patterns.recurringThemes, showsCounts: true)
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 18))
    }

    private func sectionHeader(_ title: String, subtitle: String) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title)
                .font(.headline)
                .foregroundStyle(.white)
            Text(subtitle)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private func contextMetric(title: String, value: String) -> some View {
        VStack(spacing: 3) {
            Text(value)
                .font(.headline.bold())
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
        .background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 12))
    }

    private func themeChipWrap(_ themes: [ChronicleThemeCount], showsCounts: Bool) -> some View {
        let columns = [GridItem(.adaptive(minimum: 90), spacing: 8)]
        return LazyVGrid(columns: columns, alignment: .leading, spacing: 8) {
            ForEach(themes) { theme in
                HStack(spacing: 4) {
                    Text(theme.theme)
                        .lineLimit(1)
                    if showsCounts && theme.count > 0 {
                        Text("×\(theme.count)")
                            .foregroundStyle(.secondary)
                    }
                }
                .font(.caption)
                .foregroundStyle(.white.opacity(0.82))
                .padding(.horizontal, 10)
                .padding(.vertical, 7)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(amber.opacity(0.12), in: Capsule())
            }
        }
    }

    // MARK: - Capture row

    private var captureRow: some View {
        VStack(spacing: 10) {
            Divider().opacity(0.2)

            // Type picker
            HStack(spacing: 8) {
                ForEach(["reflection", "prayer", "gratitude"], id: \.self) { t in
                    Button {
                        captureType = t
                    } label: {
                        Text(t.capitalized)
                            .font(.system(size: 10, weight: captureType == t ? .bold : .regular))
                            .foregroundStyle(captureType == t ? .black : .white.opacity(0.5))
                            .padding(.horizontal, 10).padding(.vertical, 5)
                            .background(captureType == t ? amber : Color.white.opacity(0.06), in: Capsule())
                    }
                    .buttonStyle(.plain)
                }
                Spacer()
            }
            .padding(.horizontal, 16)

            HStack(spacing: 10) {
                TextField("Write your \(captureType)…", text: $captureText, axis: .vertical)
                    .focused($captureFieldFocused)
                    .foregroundStyle(.white)
                    .tint(amber)
                    .lineLimit(1...4)
                    .padding(.horizontal, 12).padding(.vertical, 10)
                    .glassEffect(in: RoundedRectangle(cornerRadius: 12))

                Button {
                    let text = captureText
                    let type = captureType
                    captureText = ""
                    capturing = false
                    Task {
                        let cap = ChronicleCapture(type: type, note: text)
                        _ = try? await AppleAPIClient.shared.captureChronicle(cap)
                        await load()
                    }
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 30))
                        .foregroundStyle(captureText.isEmpty ? .white.opacity(0.2) : amber)
                }
                .disabled(captureText.isEmpty)
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 12)
        }
        .background(.ultraThinMaterial)
    }

    // MARK: - Error

    private func errorView(_ msg: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "book.closed.fill")
                .font(.system(size: 44)).foregroundStyle(amber.opacity(0.4))
            Text("Chronicle unavailable").font(.headline).foregroundStyle(.white)
            Text(msg).font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
            Button("Retry") { Task { await load() } }
                .buttonStyle(.borderedProminent).tint(amber)
        }
        .padding(24).glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32).frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func load() async {
        isLoading = true; error = nil
        do { overview = try await AppleAPIClient.shared.fetchChronicle() }
        catch { self.error = error.localizedDescription }
        isLoading = false
    }
}

// MARK: - Entry card

private struct EntryCard: View {
    let entry: ChronicleEntry
    let amber: Color

    var typeIcon: String {
        switch entry.type {
        case "prayer":    return "hands.sparkles"
        case "gratitude": return "heart.fill"
        case "scripture": return "book.fill"
        case "milestone": return "star.fill"
        default:          return "pencil.line"
        }
    }
    var typeColor: Color {
        switch entry.type {
        case "prayer":    return .purple
        case "gratitude": return .pink
        case "scripture": return amber
        case "milestone": return .yellow
        default:          return .white.opacity(0.6)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top) {
                // Type badge
                Label(entry.type.capitalized, systemImage: typeIcon)
                    .font(.system(size: 9, weight: .bold))
                    .tracking(0.5)
                    .foregroundStyle(typeColor)
                    .padding(.horizontal, 7).padding(.vertical, 3)
                    .background(typeColor.opacity(0.12), in: Capsule())
                Spacer()
                Text(relativeDate(entry.timestamp))
                    .font(.caption2).foregroundStyle(.secondary)
            }

            if !entry.title.isEmpty {
                Text(entry.title)
                    .font(.subheadline.bold()).foregroundStyle(.white)
            }

            if !entry.body.isEmpty {
                Text(entry.body)
                    .font(.subheadline).foregroundStyle(.white.opacity(0.8))
                    .lineLimit(4).fixedSize(horizontal: false, vertical: true)
            }

            if let scripture = entry.scripture, !scripture.isEmpty {
                Label(scripture, systemImage: "book.closed")
                    .font(.caption2).foregroundStyle(amber.opacity(0.7))
            }
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func relativeDate(_ iso: String) -> String {
        let f = ISO8601DateFormatter()
        guard let d = f.date(from: iso) else { return iso.prefix(10).description }
        return d.formatted(.relative(presentation: .named))
    }
}

#Preview { ChronicleView() }
