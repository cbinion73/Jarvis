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
    @State private var selectedStoryboardIndex = 0
    @FocusState private var captureFieldFocused: Bool

    private let amber = Color(red: 0.82, green: 0.63, blue: 0.36)
    private let ember = Color(red: 0.68, green: 0.47, blue: 0.24)
    private let panel = Color(red: 0.06, green: 0.08, blue: 0.11)
    private let panelRaised = Color(red: 0.09, green: 0.11, blue: 0.14)
    private let line = Color(red: 0.43, green: 0.32, blue: 0.18)
    private let softText = Color.white.opacity(0.68)
    private let mutedText = Color.white.opacity(0.5)

    private var storyboardStages: [ChronicleStoryboardStage] {
        [
            .init(id: "home", number: "1", title: "Chronicle Home / Memory Hub", detail: "Your memory center. Recent entries, life themes, memory lanes, and prompts."),
            .init(id: "capture", number: "2", title: "Memory Capture", detail: "Capture the moment with photo, audio, voice, text, and rich context."),
            .init(id: "thread", number: "3", title: "Story Thread", detail: "See how moments connect. Follow the timeline of a story across time and themes."),
            .init(id: "family", number: "4", title: "Family History", detail: "Explore generations, key people, important dates, and legacy stories."),
            .init(id: "reflection", number: "5", title: "Reflection / Narrative Synthesis", detail: "JARVIS weaves your memories into meaningful narratives and insights."),
            .init(id: "voice", number: "6", title: "Voice Conversation", detail: "Talk to JARVIS, record, recall, and reflect hands-free."),
        ]
    }

    var body: some View {
        NavigationStack {
            ZStack {
                ZStack {
                    Color(red: 0.01, green: 0.02, blue: 0.04)
                    LinearGradient(
                        colors: [
                            Color(red: 0.06, green: 0.05, blue: 0.03),
                            Color(red: 0.02, green: 0.03, blue: 0.05),
                            Color.black,
                        ],
                        startPoint: .top,
                        endPoint: UnitPoint(x: 0.6, y: 0.58)
                    )
                    RadialGradient(
                        colors: [amber.opacity(0.12), .clear],
                        center: .topTrailing,
                        startRadius: 10,
                        endRadius: 320
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

                memoryHubSection(ov)

                if let patterns = ov.patterns {
                    patternsSection(patterns)
                }

                if let context = ov.context {
                    contextSection(context)
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

                voiceSection(ov)

                legacyPillars

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
                    .background(panelCard(cornerRadius: 24))
                } else {
                    sectionHeader("Recent Entries", subtitle: "\(ov.entries.count) loaded from live Chronicle", number: nil)
                    ForEach(ov.entries) { entry in
                        EntryCard(entry: entry, amber: amber) { status in
                            await reviewEntry(entry, status: status)
                        }
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 16)
        }
    }

    @ViewBuilder
    private func memoryHubSection(_ ov: ChronicleOverview) -> some View {
        sectionHeader("Chronicle Home / Memory Hub", subtitle: "Your memory center. Recent entries, life themes, memory lanes, and prompts.", number: "1")
        VStack(alignment: .leading, spacing: 14) {
            heroMemoryCard

            if !ov.entries.isEmpty {
                VStack(alignment: .leading, spacing: 10) {
                    headerRow("Recent Entries", trailing: "See All")
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 10) {
                            ForEach(ov.entries.prefix(3)) { entry in
                                memoryLaneCard(entry)
                            }
                        }
                    }
                }
            }

            if let context = ov.context, !context.topThemes.isEmpty || context.totalEntries > 0 {
                VStack(alignment: .leading, spacing: 10) {
                    headerRow("Life Themes", trailing: "Live")
                    if !context.topThemes.isEmpty {
                        themeChipWrap(context.topThemes.map { ChronicleThemeCount(theme: $0, count: 0) }, showsCounts: false)
                    }
                    HStack(spacing: 10) {
                        contextMetric(title: "Memories", value: "\(context.totalEntries)")
                        contextMetric(title: "Prayers", value: "\(context.activePrayerCount)")
                        contextMetric(title: "Answered", value: "\(context.answeredPrayerCount)")
                    }
                }
            }
        }
        .padding(18)
        .background(panelCard(cornerRadius: 28))
    }

    @ViewBuilder
    private func contextSection(_ context: ChronicleContext) -> some View {
        sectionHeader("Memory Capture", subtitle: "Capture the moment with reflection, prayer, gratitude, and living context.", number: "2")
        VStack(alignment: .leading, spacing: 12) {
            if capturing {
                captureComposerPreview
            } else {
                capturePreviewCard(context)
            }

            if let study = context.study, !study.passage.isEmpty || !study.title.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Current Study")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(amber.opacity(0.85))
                    Text(study.passage.isEmpty ? study.title : study.passage)
                        .font(.system(size: 22, weight: .semibold, design: .serif))
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
                    Text("Today's Reflection Rhythm")
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
        .background(panelCard(cornerRadius: 24))
    }

    private var conceptHeader: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("JARVIS Chronicle Experience")
                        .font(.system(size: 34, weight: .semibold, design: .serif))
                        .foregroundStyle(.white)
                    Text("Concept Storyboard")
                        .font(.system(size: 17, weight: .regular, design: .serif))
                        .foregroundStyle(softText)
                }
                Spacer()
                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 10) {
                        Image(systemName: "feather")
                            .font(.system(size: 15, weight: .medium))
                            .foregroundStyle(amber)
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Every moment matters.")
                                .font(.system(size: 14, weight: .semibold, design: .serif))
                                .foregroundStyle(.white.opacity(0.92))
                            Text("Every story deserves to be remembered.")
                                .font(.system(size: 14, weight: .regular, design: .serif))
                                .foregroundStyle(softText)
                        }
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
                    .background(panelCard(cornerRadius: 18))
                }
            }

            VStack(alignment: .leading, spacing: 12) {
                TabView(selection: $selectedStoryboardIndex) {
                    ForEach(Array(storyboardStages.enumerated()), id: \.element.id) { index, stage in
                        storyboardCard(stage)
                            .tag(index)
                    }
                }
                .tabViewStyle(.page(indexDisplayMode: .never))
                .frame(height: 112)

                HStack(spacing: 12) {
                    Button {
                        withAnimation(.easeInOut(duration: 0.22)) {
                            selectedStoryboardIndex = max(0, selectedStoryboardIndex - 1)
                        }
                    } label: {
                        Image(systemName: "arrow.left")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(selectedStoryboardIndex == 0 ? mutedText : amber)
                            .frame(width: 34, height: 34)
                            .background(panel, in: Circle())
                            .overlay(Circle().stroke(line.opacity(0.82), lineWidth: 1))
                    }
                    .buttonStyle(.plain)
                    .disabled(selectedStoryboardIndex == 0)

                    Text("Page \(selectedStoryboardIndex + 1) of \(storyboardStages.count)")
                        .font(.caption.weight(.medium))
                        .foregroundStyle(softText)

                    Spacer()

                    Button {
                        withAnimation(.easeInOut(duration: 0.22)) {
                            selectedStoryboardIndex = min(storyboardStages.count - 1, selectedStoryboardIndex + 1)
                        }
                    } label: {
                        Image(systemName: "arrow.right")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(selectedStoryboardIndex == storyboardStages.count - 1 ? mutedText : amber)
                            .frame(width: 34, height: 34)
                            .background(panel, in: Circle())
                            .overlay(Circle().stroke(line.opacity(0.82), lineWidth: 1))
                    }
                    .buttonStyle(.plain)
                    .disabled(selectedStoryboardIndex == storyboardStages.count - 1)
                }
            }

            HStack(spacing: 10) {
                capabilityPill(title: "Your Life, Beautifully Preserved", detail: "Capture moments, big and small.")
                capabilityPill(title: "Generations Connected", detail: "Honor your past. Inspire your future.")
                capabilityPill(title: "Living Story Engine", detail: "JARVIS helps your story shine.")
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
                    Color(red: 0.31, green: 0.22, blue: 0.11),
                    Color(red: 0.12, green: 0.11, blue: 0.08),
                    Color(red: 0.04, green: 0.05, blue: 0.08),
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .overlay {
                LinearGradient(
                    colors: [.clear, Color.black.opacity(0.54)],
                    startPoint: .center,
                    endPoint: .bottom
                )
            }
            VStack(alignment: .leading, spacing: 10) {
                Text("Good evening, Chris.")
                    .font(.system(size: 28, weight: .semibold, design: .serif))
                    .foregroundStyle(.white)
                Text(entryTitle ?? "Chronicle")
                    .font(.system(size: 15, weight: .medium, design: .serif))
                    .foregroundStyle(softText)
                Text(subtitle ?? "")
                    .font(.system(size: 18, weight: .regular, design: .serif))
                    .foregroundStyle(.white)
                    .lineLimit(3)
                HStack(spacing: 8) {
                    contextMetricChip(title: "Entries", value: "\(overview?.entries.count ?? 0)")
                    contextMetricChip(title: "Themes", value: "\(overview?.patterns?.recurringThemes.count ?? 0)")
                    contextMetricChip(title: "Prayers", value: "\(overview?.context?.activePrayerCount ?? 0)")
                }
            }
            .padding(18)
        }
        .frame(maxWidth: .infinity, minHeight: 220, alignment: .bottomLeading)
        .clipShape(RoundedRectangle(cornerRadius: 22))
        .overlay(
            RoundedRectangle(cornerRadius: 22)
                .stroke(line.opacity(0.85), lineWidth: 1)
        )
    }

    @ViewBuilder
    private func studyWorkspaceSection(_ workspace: ChronicleStudyWorkspace) -> some View {
        sectionHeader("Reflection / Narrative Synthesis", subtitle: "JARVIS weaves your memories into meaningful narratives and study posture.", number: "5")
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(workspace.title)
                        .font(.system(size: 24, weight: .semibold, design: .serif))
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
        .background(panelCard(cornerRadius: 24))
    }

    @ViewBuilder
    private func patternsSection(_ patterns: ChroniclePatterns) -> some View {
        sectionHeader("Story Thread", subtitle: "See how moments connect. Follow the timeline of recurring themes and prayer arcs.", number: "3")
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
        .background(panelCard(cornerRadius: 24))
    }

    @ViewBuilder
    private func continuitySection(_ continuity: ChronicleContinuity) -> some View {
        if !continuity.relevantFacts.isEmpty || !continuity.similarEntries.isEmpty || !continuity.situations.isEmpty || !continuity.recallPrompt.isEmpty {
            sectionHeader("Family History", subtitle: "Explore generations, durable facts, similar moments, and legacy continuity.", number: "4")
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 10) {
                    contextMetric(title: "Source-Backed Records", value: "\(continuity.relevantFacts.count)")
                    contextMetric(title: "Open Questions", value: "\(continuity.situations.count)")
                    contextMetric(title: "Timeline Links", value: "\(continuity.similarEntries.count)")
                }

                if !continuity.recallPrompt.isEmpty {
                    Text(continuity.recallPrompt)
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.86))
                }

                if !familyLineTokens(from: continuity).isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Family Lines")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(amber.opacity(0.85))
                        LazyVGrid(columns: [GridItem(.adaptive(minimum: 96), spacing: 8)], alignment: .leading, spacing: 8) {
                            ForEach(familyLineTokens(from: continuity), id: \.self) { token in
                                HStack(spacing: 6) {
                                    Image(systemName: "person.2")
                                        .font(.caption2)
                                    Text(token)
                                        .lineLimit(1)
                                }
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.86))
                                .padding(.horizontal, 10)
                                .padding(.vertical, 8)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(panelRaised, in: RoundedRectangle(cornerRadius: 14))
                                .overlay(RoundedRectangle(cornerRadius: 14).stroke(line.opacity(0.55), lineWidth: 1))
                            }
                        }
                    }
                }

                if !continuity.situations.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Open Research Questions")
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
                            .background(panelRaised, in: RoundedRectangle(cornerRadius: 12))
                            .overlay(RoundedRectangle(cornerRadius: 12).stroke(line.opacity(0.55), lineWidth: 1))
                        }
                    }
                }

                if !continuity.relevantFacts.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Evidence Ledger")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(amber.opacity(0.85))
                        ForEach(continuity.relevantFacts) { fact in
                            VStack(alignment: .leading, spacing: 4) {
                                HStack(alignment: .top, spacing: 8) {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(fact.title)
                                            .font(.subheadline.bold())
                                            .foregroundStyle(.white)
                                        Text(fact.summary)
                                            .font(.caption)
                                            .foregroundStyle(.white.opacity(0.78))
                                    }
                                    Spacer()
                                    VStack(alignment: .trailing, spacing: 4) {
                                        Text(fact.lane.isEmpty ? "record" : fact.lane.replacingOccurrences(of: "_", with: " ").capitalized)
                                            .font(.caption2.weight(.semibold))
                                            .foregroundStyle(amber.opacity(0.9))
                                        if !fact.updatedAt.isEmpty {
                                            Text(shortDate(fact.updatedAt))
                                                .font(.caption2)
                                                .foregroundStyle(mutedText)
                                        }
                                    }
                                }
                                if !fact.tags.isEmpty || !fact.lane.isEmpty {
                                    Text(([fact.lane] + fact.tags).filter { !$0.isEmpty }.prefix(4).joined(separator: " · "))
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .padding(12)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(panelRaised, in: RoundedRectangle(cornerRadius: 12))
                            .overlay(RoundedRectangle(cornerRadius: 12).stroke(line.opacity(0.55), lineWidth: 1))
                        }
                    }
                }

                if !continuity.similarEntries.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Timeline Evidence")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(amber.opacity(0.85))
                        ForEach(continuity.similarEntries.prefix(2)) { entry in
                            genealogyTimelineCard(entry)
                        }
                    }
                }
            }
            .padding(16)
            .background(panelCard(cornerRadius: 24))
        }
    }

    @ViewBuilder
    private func reviewLaneSection(_ reviews: [ChronicleReviewEntry]) -> some View {
        sectionHeader("Review Lane", subtitle: "\(reviews.count) Chronicle thread\(reviews.count == 1 ? "" : "s") with durable follow-up", number: nil)
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
        .background(panelCard(cornerRadius: 24))
    }

    @ViewBuilder
    private func voiceSection(_ ov: ChronicleOverview) -> some View {
        sectionHeader("Voice Conversation", subtitle: "Talk to JARVIS, record, recall, and reflect hands-free.", number: "6")
        VStack(alignment: .leading, spacing: 14) {
            voiceBubble(
                speaker: "You",
                body: ov.entries.first?.title.isEmpty == false
                    ? "Tell me more about \(ov.entries.first?.title ?? "that memory")."
                    : "Help me revisit this week and tell me what mattered most.",
                emphasized: false
            )
            voiceBubble(
                speaker: "JARVIS",
                body: ov.continuity?.recallPrompt.isEmpty == false
                    ? ov.continuity?.recallPrompt ?? ""
                    : "I can connect your recent entries, active prayers, and recurring themes into one living story thread.",
                emphasized: true
            )

            if let entry = ov.entries.first {
                HStack(spacing: 12) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(entry.title.isEmpty ? "Latest Memory" : entry.title)
                            .font(.system(size: 16, weight: .semibold, design: .serif))
                            .foregroundStyle(.white)
                        Text(relativeDate(entry.timestamp))
                            .font(.caption)
                            .foregroundStyle(mutedText)
                    }
                    Spacer()
                    Image(systemName: "play.fill")
                        .font(.caption.bold())
                        .foregroundStyle(.black)
                        .frame(width: 34, height: 34)
                        .background(amber, in: Circle())
                }
                .padding(14)
                .background(panelRaised, in: RoundedRectangle(cornerRadius: 18))
            }
        }
        .padding(16)
        .background(panelCard(cornerRadius: 24))
    }

    private var legacyPillars: some View {
        VStack(spacing: 12) {
            HStack(spacing: 10) {
                footerPillar(icon: "book.closed", title: "Your Life, Beautifully Preserved", detail: "Capture moments, big and small. Your story matters.")
                footerPillar(icon: "tree", title: "Generations Connected", detail: "Honor your past. Inspire your future.")
            }
            HStack(spacing: 10) {
                footerPillar(icon: "heart", title: "Meaning Over Time", detail: "JARVIS turns moments into wisdom and legacy.")
                footerPillar(icon: "lock", title: "Private & Secure", detail: "Your memories are yours. End-to-end encrypted.")
            }
        }
    }

    private func sectionHeader(_ title: String, subtitle: String, number: String?) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack(spacing: 10) {
                if let number {
                    Text(number)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(amber)
                        .frame(width: 22, height: 22)
                        .overlay(Circle().stroke(line, lineWidth: 1))
                }
                Text(title)
                    .font(.system(size: 26, weight: .semibold, design: .serif))
                    .foregroundStyle(.white)
            }
            Text(subtitle)
                .font(.subheadline)
                .foregroundStyle(softText)
        }
    }

    private func contextMetric(title: String, value: String) -> some View {
        VStack(spacing: 3) {
            Text(value)
                .font(.headline.bold())
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(mutedText)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
        .background(panelRaised, in: RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(line.opacity(0.55), lineWidth: 1)
        )
    }

    private func contextMetricChip(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(value)
                .font(.caption.weight(.bold))
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(mutedText)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(Color.black.opacity(0.22), in: RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(line.opacity(0.65), lineWidth: 1)
        )
    }

    private func storyboardCard(_ stage: ChronicleStoryboardStage) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Text(stage.number)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(amber)
                    .frame(width: 22, height: 22)
                    .overlay(Circle().stroke(line, lineWidth: 1))
                Text(stage.title)
                    .font(.system(size: 15, weight: .semibold, design: .serif))
                    .foregroundStyle(.white.opacity(0.92))
            }
            Text(stage.detail)
                .font(.caption)
                .foregroundStyle(softText)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .background(panel, in: RoundedRectangle(cornerRadius: 18))
        .overlay(
            RoundedRectangle(cornerRadius: 18)
                .stroke(line.opacity(0.82), lineWidth: 1)
        )
    }

    private func capabilityPill(title: String, detail: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.system(size: 13, weight: .semibold, design: .serif))
                .foregroundStyle(amber.opacity(0.9))
            Text(detail)
                .font(.caption)
                .foregroundStyle(softText)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(panel, in: RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(line.opacity(0.82), lineWidth: 1)
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
                .overlay(Capsule().stroke(line.opacity(0.55), lineWidth: 1))
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
                .tint(prayer.answered ? .green : amber)
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
            Divider().overlay(line.opacity(0.5))

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
                    .background(panelRaised, in: RoundedRectangle(cornerRadius: 12))

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
        .background(panel.opacity(0.98))
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
                    .background(panelRaised, in: RoundedRectangle(cornerRadius: 14))

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
                            .tint(amber)

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
                        .background(panelRaised, in: RoundedRectangle(cornerRadius: 14))

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
        .padding(24)
        .background(panelCard(cornerRadius: 20))
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

    private func panelCard(cornerRadius: CGFloat) -> some View {
        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
            .fill(
                LinearGradient(
                    colors: [panelRaised.opacity(0.98), panel.opacity(0.98)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .stroke(line.opacity(0.85), lineWidth: 1)
            )
    }

    private func headerRow(_ title: String, trailing: String) -> some View {
        HStack {
            Text(title)
                .font(.system(size: 15, weight: .semibold, design: .serif))
                .foregroundStyle(.white)
            Spacer()
            Text(trailing)
                .font(.caption)
                .foregroundStyle(amber)
        }
    }

    private func familyLineTokens(from continuity: ChronicleContinuity) -> [String] {
        let candidates = continuity.relevantFacts.flatMap { fact in
            ([fact.lane] + fact.tags).filter { !$0.isEmpty }
        }
        var seen = Set<String>()
        return candidates
            .map { $0.replacingOccurrences(of: "_", with: " ").capitalized }
            .filter { token in
                let key = token.lowercased()
                guard !seen.contains(key) else { return false }
                seen.insert(key)
                return true
            }
            .prefix(6)
            .map { $0 }
    }

    private func shortDate(_ value: String) -> String {
        let formatter = ISO8601DateFormatter()
        guard let date = formatter.date(from: value) else {
            return String(value.prefix(10))
        }
        return date.formatted(date: .abbreviated, time: .omitted)
    }

    private func genealogyTimelineCard(_ entry: ChronicleEntry) -> some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(spacing: 0) {
                Circle()
                    .fill(amber)
                    .frame(width: 10, height: 10)
                Rectangle()
                    .fill(line.opacity(0.75))
                    .frame(width: 1, height: 52)
            }

            VStack(alignment: .leading, spacing: 6) {
                Text(relativeDate(entry.timestamp))
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(amber.opacity(0.9))
                Text(entry.title.isEmpty ? "Family memory" : entry.title)
                    .font(.system(size: 16, weight: .semibold, design: .serif))
                    .foregroundStyle(.white)
                Text(entry.body.isEmpty ? "Linked into the family timeline for later verification and storytelling." : entry.body)
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.78))
                    .lineLimit(3)
            }
            Spacer()
        }
        .padding(12)
        .background(panelRaised, in: RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(line.opacity(0.55), lineWidth: 1))
    }

    private func memoryLaneCard(_ entry: ChronicleEntry) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            RoundedRectangle(cornerRadius: 16)
                .fill(
                    LinearGradient(
                        colors: [ember.opacity(0.85), panelRaised],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .frame(height: 88)
                .overlay(alignment: .bottomLeading) {
                    Text(entry.type.capitalized)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.9))
                        .padding(10)
                }
            Text(entry.title.isEmpty ? "Untitled memory" : entry.title)
                .font(.system(size: 15, weight: .semibold, design: .serif))
                .foregroundStyle(.white)
                .lineLimit(2)
            Text(relativeDate(entry.timestamp))
                .font(.caption)
                .foregroundStyle(mutedText)
        }
        .frame(width: 156, alignment: .leading)
        .padding(10)
        .background(panelRaised, in: RoundedRectangle(cornerRadius: 18))
        .overlay(RoundedRectangle(cornerRadius: 18).stroke(line.opacity(0.55), lineWidth: 1))
    }

    private func capturePreviewCard(_ context: ChronicleContext) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            RoundedRectangle(cornerRadius: 18)
                .fill(
                    LinearGradient(
                        colors: [ember.opacity(0.95), panelRaised],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .frame(height: 170)
                .overlay(alignment: .bottomLeading) {
                    Text("Worth remembering...")
                        .font(.system(size: 18, weight: .semibold, design: .serif))
                        .foregroundStyle(.white)
                        .padding(16)
                }

            HStack(spacing: 10) {
                captureModePill("Photo", icon: "camera")
                captureModePill("Audio", icon: "waveform")
                captureModePill("Voice", icon: "mic")
                captureModePill("Text", icon: "text.alignleft")
            }

            HStack(spacing: 10) {
                infoChip("Entries", "\(context.totalEntries)")
                infoChip("Prayers", "\(context.activePrayerCount)")
                infoChip("Themes", "\(context.topThemes.count)")
            }
        }
    }

    private var captureComposerPreview: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("New Memory")
                .font(.system(size: 18, weight: .semibold, design: .serif))
                .foregroundStyle(.white)
            Text("Capture is open below. Add the reflection while the moment is still alive.")
                .font(.caption)
                .foregroundStyle(softText)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(panelRaised, in: RoundedRectangle(cornerRadius: 18))
        .overlay(RoundedRectangle(cornerRadius: 18).stroke(line.opacity(0.55), lineWidth: 1))
    }

    private func captureModePill(_ title: String, icon: String) -> some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.caption.weight(.semibold))
            Text(title)
                .font(.caption2)
        }
        .foregroundStyle(.white.opacity(0.86))
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
        .background(panelRaised, in: RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(line.opacity(0.55), lineWidth: 1))
    }

    private func infoChip(_ title: String, _ value: String) -> some View {
        HStack(spacing: 6) {
            Text(title)
                .font(.caption)
                .foregroundStyle(mutedText)
            Text(value)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.white)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(panelRaised, in: Capsule())
        .overlay(Capsule().stroke(line.opacity(0.55), lineWidth: 1))
    }

    private func voiceBubble(speaker: String, body: String, emphasized: Bool) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(speaker)
                .font(.caption.weight(.semibold))
                .foregroundStyle(emphasized ? amber : softText)
            Text(body)
                .font(.body)
                .foregroundStyle(.white.opacity(0.9))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background((emphasized ? amber.opacity(0.12) : panelRaised), in: RoundedRectangle(cornerRadius: 18))
        .overlay(RoundedRectangle(cornerRadius: 18).stroke(line.opacity(0.55), lineWidth: 1))
    }

    private func footerPillar(icon: String, title: String, detail: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 24, weight: .regular))
                .foregroundStyle(amber)
                .frame(width: 28)
            VStack(alignment: .leading, spacing: 5) {
                Text(title)
                    .font(.system(size: 15, weight: .semibold, design: .serif))
                    .foregroundStyle(.white)
                Text(detail)
                    .font(.caption)
                    .foregroundStyle(softText)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(panel, in: RoundedRectangle(cornerRadius: 18))
        .overlay(RoundedRectangle(cornerRadius: 18).stroke(line.opacity(0.82), lineWidth: 1))
    }

    private func relativeDate(_ iso: String) -> String {
        let f = ISO8601DateFormatter()
        guard let d = f.date(from: iso) else { return iso.prefix(10).description }
        return d.formatted(.relative(presentation: .named))
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
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color(red: 0.09, green: 0.11, blue: 0.14).opacity(0.98),
                            Color(red: 0.05, green: 0.07, blue: 0.1).opacity(0.98),
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .stroke(Color(red: 0.43, green: 0.32, blue: 0.18).opacity(0.82), lineWidth: 1)
                )
        )
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
        let formatter = ISO8601DateFormatter()
        guard let date = formatter.date(from: iso) else { return iso.prefix(10).description }
        return date.formatted(.relative(presentation: .named))
    }

}

#Preview { ChronicleView() }
