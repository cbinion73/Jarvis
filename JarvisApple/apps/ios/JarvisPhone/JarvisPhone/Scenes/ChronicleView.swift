import SwiftUI
import JarvisKit

// MARK: - ChronicleView  "The Journal"
// Disciple · Chronicle & Reflection

struct ChronicleView: View {

    private struct ChronicleStoryboardStage: Identifiable {
        let id: String
        let number: String
        let title: String
        let detail: String
    }

    @State private var overview: ChronicleOverview?
    @State private var isLoading  = false
    @State private var error: String?
    @State private var capturing  = false
    @State private var captureType = "reflection"
    @State private var captureText = ""
    @State private var selectedPrayer: ChroniclePrayer?
    @State private var prayerNote = ""
    @State private var studyDraft = ""
    @State private var showingStudyWorkspace = false
    @FocusState private var captureFieldFocused: Bool

    private let amber = Color(red: 0.9, green: 0.65, blue: 0.25)

    private var storyboardStages: [ChronicleStoryboardStage] {
        [
            .init(id: "home", number: "1", title: "Memory Hub", detail: "Recent entries, themes, and living prompts."),
            .init(id: "capture", number: "2", title: "Capture", detail: "Reflection, prayer, gratitude, and notes."),
            .init(id: "thread", number: "3", title: "Story Thread", detail: "Connected moments and recurring themes."),
            .init(id: "family", number: "4", title: "Family History", detail: "People, prayers, and legacy continuity."),
            .init(id: "reflection", number: "5", title: "Reflection", detail: "Narrative synthesis and study posture."),
            .init(id: "voice", number: "6", title: "Voice", detail: "Hands-free recall and follow-up."),
        ]
    }

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
            .sheet(item: $selectedPrayer) { prayer in
                prayerActionSheet(prayer)
            }
            .sheet(isPresented: $showingStudyWorkspace) {
                if let workspace = overview?.studyWorkspace {
                    studyWorkspaceSheet(workspace)
                }
            }
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
                conceptHeader

                if let context = ov.context {
                    contextSection(context)
                }

                if let patterns = ov.patterns {
                    patternsSection(patterns)
                }

                if let continuity = ov.continuity {
                    continuitySection(continuity)
                }

                if let studyWorkspace = ov.studyWorkspace {
                    studyWorkspaceSection(studyWorkspace)
                }

                if !ov.reviewLane.isEmpty {
                    reviewLaneSection(ov.reviewLane)
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
                        EntryCard(entry: entry, amber: amber) { status in
                            await reviewEntry(entry, status: status)
                        }
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
                        prayerRow(prayer)
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

    private var conceptHeader: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("JARVIS")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .tracking(2.0)
                        .foregroundStyle(amber.opacity(0.92))
                    Text("Chronicle")
                        .font(.system(size: 30, weight: .bold, design: .rounded))
                        .foregroundStyle(.white)
                    Text("Concept storyboard with live memory, prayer, and study continuity.")
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.68))
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 6) {
                    HStack(spacing: 8) {
                        Image(systemName: "feather.fill")
                            .font(.caption.bold())
                            .foregroundStyle(amber)
                        Text("EVERY MOMENT MATTERS")
                            .font(.caption2.weight(.semibold))
                            .tracking(1.1)
                            .foregroundStyle(.white.opacity(0.72))
                    }
                    Text("Your life, beautifully preserved.")
                        .font(.caption2)
                        .foregroundStyle(.white.opacity(0.48))
                }
            }

            heroMemoryCard

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    ForEach(storyboardStages) { stage in
                        storyboardCard(stage)
                    }
                }
                .padding(.vertical, 2)
            }

            HStack(spacing: 10) {
                capabilityPill(title: "Life Themes", detail: "Meaning over time")
                capabilityPill(title: "Family", detail: "Generations connected")
                capabilityPill(title: "Voice", detail: "Living story engine")
            }
        }
    }

    private var heroMemoryCard: some View {
        let entryTitle = overview?.entries.first?.title.isEmpty == false
            ? overview?.entries.first?.title
            : "Your story is being written one moment at a time."
        let subtitle = overview?.entries.first?.body.isEmpty == false
            ? overview?.entries.first?.body
            : "Recent reflections, prayer arcs, and study context stay connected in one living memory lane."

        return ZStack(alignment: .bottomLeading) {
            LinearGradient(
                colors: [
                    Color(red: 0.19, green: 0.13, blue: 0.06),
                    Color(red: 0.09, green: 0.07, blue: 0.03),
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            VStack(alignment: .leading, spacing: 10) {
                Text("Good evening, Chris.")
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white)
                Text(entryTitle ?? "Chronicle")
                    .font(.title3.bold())
                    .foregroundStyle(.white)
                Text(subtitle ?? "")
                    .font(.subheadline)
                    .foregroundStyle(.white.opacity(0.76))
                    .lineLimit(3)
                HStack(spacing: 8) {
                    contextMetricChip(title: "Entries", value: "\(overview?.entries.count ?? 0)")
                    contextMetricChip(title: "Themes", value: "\(overview?.patterns?.recurringThemes.count ?? 0)")
                    contextMetricChip(title: "Prayers", value: "\(overview?.context?.activePrayerCount ?? 0)")
                }
            }
            .padding(18)
        }
        .frame(maxWidth: .infinity, minHeight: 170, alignment: .bottomLeading)
        .clipShape(RoundedRectangle(cornerRadius: 22))
        .overlay(
            RoundedRectangle(cornerRadius: 22)
                .stroke(.white.opacity(0.08), lineWidth: 1)
        )
    }

    @ViewBuilder
    private func studyWorkspaceSection(_ workspace: ChronicleStudyWorkspace) -> some View {
        sectionHeader("Study Workflow", subtitle: "Save deeper study reflections back into Chronicle")
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(workspace.title)
                        .font(.headline)
                        .foregroundStyle(.white)
                    if !workspace.passage.isEmpty {
                        Text(workspace.passage)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(amber.opacity(0.9))
                    }
                    if !workspace.focusSummary.isEmpty {
                        Text(workspace.focusSummary)
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.72))
                    }
                }
                Spacer()
                Button("Open Study") {
                    studyDraft = ""
                    showingStudyWorkspace = true
                }
                .buttonStyle(.borderedProminent)
                .tint(amber)
            }

            if !workspace.prompts.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(workspace.prompts, id: \.self) { prompt in
                        HStack(alignment: .top, spacing: 8) {
                            Image(systemName: "text.quote")
                                .font(.caption2)
                                .foregroundStyle(amber.opacity(0.85))
                                .padding(.top, 2)
                            Text(prompt)
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.8))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
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

    @ViewBuilder
    private func continuitySection(_ continuity: ChronicleContinuity) -> some View {
        if !continuity.relevantFacts.isEmpty || !continuity.similarEntries.isEmpty || !continuity.situations.isEmpty || !continuity.recallPrompt.isEmpty {
            sectionHeader("How We Handled This Before", subtitle: "Durable continuity from memory and Chronicle history")
            VStack(alignment: .leading, spacing: 12) {
                if !continuity.recallPrompt.isEmpty {
                    Text(continuity.recallPrompt)
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.86))
                }

                if !continuity.situations.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Situation Matches")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(amber.opacity(0.85))
                        ForEach(continuity.situations.prefix(2)) { situation in
                            VStack(alignment: .leading, spacing: 6) {
                                HStack(alignment: .center, spacing: 8) {
                                    Text(situation.label)
                                        .font(.subheadline.bold())
                                        .foregroundStyle(.white)
                                    if situation.matchedFactCount > 0 {
                                        Text("\(situation.matchedFactCount) fact\(situation.matchedFactCount == 1 ? "" : "s")")
                                            .font(.caption2.weight(.semibold))
                                            .foregroundStyle(amber.opacity(0.85))
                                            .padding(.horizontal, 8)
                                            .padding(.vertical, 4)
                                            .background(amber.opacity(0.12), in: Capsule())
                                    }
                                }
                                Text(situation.summary)
                                    .font(.caption)
                                    .foregroundStyle(.white.opacity(0.78))
                                if !situation.signals.isEmpty {
                                    Text(situation.signals.prefix(4).joined(separator: " · "))
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .padding(12)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 12))
                        }
                    }
                }

                if !continuity.relevantFacts.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Durable Facts")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(amber.opacity(0.85))
                        ForEach(continuity.relevantFacts) { fact in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(fact.title)
                                    .font(.subheadline.bold())
                                    .foregroundStyle(.white)
                                Text(fact.summary)
                                    .font(.caption)
                                    .foregroundStyle(.white.opacity(0.78))
                                if !fact.tags.isEmpty {
                                    Text(fact.tags.prefix(3).joined(separator: " · "))
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .padding(12)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 12))
                        }
                    }
                }

                if !continuity.similarEntries.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Similar Moments")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(amber.opacity(0.85))
                        ForEach(continuity.similarEntries.prefix(2)) { entry in
                            EntryCard(entry: entry, amber: amber)
                        }
                    }
                }
            }
            .padding(16)
            .glassEffect(in: RoundedRectangle(cornerRadius: 18))
        }
    }

    @ViewBuilder
    private func reviewLaneSection(_ reviews: [ChronicleReviewEntry]) -> some View {
        sectionHeader("Review Lane", subtitle: "\(reviews.count) Chronicle thread\(reviews.count == 1 ? "" : "s") with durable follow-up")
        VStack(alignment: .leading, spacing: 10) {
            ForEach(reviews.prefix(4)) { review in
                VStack(alignment: .leading, spacing: 6) {
                    HStack(alignment: .center, spacing: 8) {
                        Text(review.entryTitle)
                            .font(.subheadline.bold())
                            .foregroundStyle(.white)
                        Spacer()
                        Text(review.reviewStatusLabel)
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(amber.opacity(0.95))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(amber.opacity(0.14), in: Capsule())
                    }
                    Text([review.entryType.capitalized, review.reviewNote].filter { !$0.isEmpty }.joined(separator: " · "))
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.72))
                }
                .padding(12)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 12))
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

    private func contextMetricChip(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(value)
                .font(.caption.weight(.bold))
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.58))
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
    }

    private func storyboardCard(_ stage: ChronicleStoryboardStage) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Text(stage.number)
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.black)
                    .frame(width: 22, height: 22)
                    .background(amber, in: Circle())
                Text(stage.title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.92))
            }
            Text(stage.detail)
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.6))
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(width: 158, alignment: .leading)
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(.white.opacity(0.05), lineWidth: 1)
        )
    }

    private func capabilityPill(title: String, detail: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption2.weight(.bold))
                .foregroundStyle(amber.opacity(0.9))
            Text(detail)
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.68))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(.white.opacity(0.05), lineWidth: 1)
        )
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

    private func prayerRow(_ prayer: ChroniclePrayer) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: prayer.answered ? "checkmark.seal.fill" : "hands.sparkles.fill")
                    .font(.caption2)
                    .foregroundStyle((prayer.answered ? Color.green : Color.purple).opacity(0.9))
                VStack(alignment: .leading, spacing: 3) {
                    Text(prayer.text)
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.84))
                    HStack(spacing: 6) {
                        if !prayer.category.isEmpty {
                            Text(prayer.category)
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                        if prayer.timesPrayed > 0 {
                            Text("Prayed \(prayer.timesPrayed)x")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                        if prayer.answered {
                            Text("Answered")
                                .font(.caption2.weight(.semibold))
                                .foregroundStyle(.green.opacity(0.9))
                        }
                    }
                    if let answerSummary = prayer.answerSummary, !answerSummary.isEmpty {
                        Text(answerSummary)
                            .font(.caption2)
                            .foregroundStyle(.white.opacity(0.65))
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                Spacer()
            }

            HStack(spacing: 8) {
                Button(prayer.answered ? "Answered" : "Log Prayer") {
                    prayerNote = ""
                    selectedPrayer = prayer
                }
                .buttonStyle(.bordered)
                .tint(prayer.answered ? .green : .purple)
                .disabled(prayer.answered)

                if !prayer.answered {
                    Button("Mark Answered") {
                        prayerNote = ""
                        selectedPrayer = prayer
                    }
                    .buttonStyle(.bordered)
                    .tint(.green)
                }
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

    private func prayerActionSheet(_ prayer: ChroniclePrayer) -> some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()
                VStack(alignment: .leading, spacing: 16) {
                    Text(prayer.text)
                        .font(.headline)
                        .foregroundStyle(.white)
                    TextField(
                        prayer.answered ? "Answer summary…" : "Optional prayer note…",
                        text: $prayerNote,
                        axis: .vertical
                    )
                    .lineLimit(3...6)
                    .foregroundStyle(.white)
                    .tint(amber)
                    .padding(12)
                    .glassEffect(in: RoundedRectangle(cornerRadius: 14))

                    HStack(spacing: 10) {
                        if !prayer.answered {
                            Button("Log Prayed") {
                                Task {
                                    _ = try? await AppleAPIClient.shared.markChroniclePrayerPrayed(
                                        prayer.id,
                                        payload: ChroniclePrayerActionPayload(note: prayerNote)
                                    )
                                    selectedPrayer = nil
                                    prayerNote = ""
                                    await load()
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(.purple)

                            Button("Mark Answered") {
                                Task {
                                    _ = try? await AppleAPIClient.shared.markChroniclePrayerAnswered(
                                        prayer.id,
                                        payload: ChroniclePrayerActionPayload(note: prayerNote)
                                    )
                                    selectedPrayer = nil
                                    prayerNote = ""
                                    await load()
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(.green)
                        } else {
                            Button("Done") {
                                selectedPrayer = nil
                                prayerNote = ""
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(.green)
                        }
                    }

                    Spacer()
                }
                .padding(20)
            }
            .navigationTitle("Prayer Follow-up")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private func studyWorkspaceSheet(_ workspace: ChronicleStudyWorkspace) -> some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()
                VStack(alignment: .leading, spacing: 16) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(workspace.title)
                            .font(.headline)
                            .foregroundStyle(.white)
                        if !workspace.passage.isEmpty {
                            Text(workspace.passage)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(amber.opacity(0.9))
                        }
                    }

                    if !workspace.prompts.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            ForEach(workspace.prompts, id: \.self) { prompt in
                                Text(prompt)
                                    .font(.caption)
                                    .foregroundStyle(.white.opacity(0.75))
                            }
                        }
                    }

                    TextField("Write your study reflection…", text: $studyDraft, axis: .vertical)
                        .lineLimit(8...14)
                        .foregroundStyle(.white)
                        .tint(amber)
                        .padding(12)
                        .glassEffect(in: RoundedRectangle(cornerRadius: 14))

                    Button("Save to Chronicle") {
                        Task {
                            let title = workspace.title.isEmpty ? "Bible Study" : workspace.title
                            _ = try? await AppleAPIClient.shared.saveChronicleStudy(
                                ChronicleStudySavePayload(
                                    title: title,
                                    passage: workspace.passage,
                                    notes: studyDraft
                                )
                            )
                            showingStudyWorkspace = false
                            studyDraft = ""
                            await load()
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(amber)
                    .disabled(studyDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

                    Spacer()
                }
                .padding(20)
            }
            .navigationTitle("Study")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Close") {
                        showingStudyWorkspace = false
                    }
                }
            }
        }
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

    private func reviewEntry(_ entry: ChronicleEntry, status: String) async {
        let payload = ChronicleReviewPayload(
            status: status,
            title: entry.title.isEmpty ? "Chronicle entry" : entry.title,
            entryType: entry.type
        )
        _ = try? await AppleAPIClient.shared.reviewChronicleEntry(entry.id, payload: payload)
        await load()
    }
}

// MARK: - Entry card

private struct EntryCard: View {
    let entry: ChronicleEntry
    let amber: Color
    var onReview: (@Sendable (String) async -> Void)? = nil

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

            if let onReview {
                HStack(spacing: 8) {
                    reviewButton("Study Next", tint: amber) {
                        await onReview("study")
                    }
                    reviewButton("Family Handoff", tint: .blue) {
                        await onReview("family")
                    }
                    reviewButton("Resolve", tint: .green) {
                        await onReview("resolved")
                    }
                }
                .padding(.top, 2)
            }
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func reviewButton(_ title: String, tint: Color, action: @escaping @Sendable () async -> Void) -> some View {
        Button(title) {
            Task { await action() }
        }
        .font(.caption2.weight(.semibold))
        .buttonStyle(.bordered)
        .tint(tint)
    }

    private func relativeDate(_ iso: String) -> String {
        let f = ISO8601DateFormatter()
        guard let d = f.date(from: iso) else { return iso.prefix(10).description }
        return d.formatted(.relative(presentation: .named))
    }
}

#Preview { ChronicleView() }
