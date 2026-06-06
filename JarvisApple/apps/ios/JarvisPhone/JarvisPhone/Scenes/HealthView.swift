import SwiftUI
import JarvisKit

// MARK: - HealthView  "Vitals Monitor"

struct HealthView: View {

    @ObservedObject var viewModel: HealthViewModel
    @ObservedObject private var syncManager = HealthSyncManager.shared
    @State private var checkinSymptoms = ""
    @State private var checkinNote = ""
    @State private var checkinEnergy = 5.0
    @State private var checkinSleep = 7.0
    @State private var checkinStress = 4.0
    @State private var isSavingCheckin = false
    @State private var checkinStatusMessage = "Capture a manual health check-in when live signals are sparse or you want extra context."

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                Group {
                    if viewModel.isLoading && viewModel.summary == nil {
                        loadingView
                    } else if let summary = viewModel.summary {
                        summaryView(summary)
                    } else if let error = viewModel.errorMessage {
                        errorView(error)
                    }
                }
            }
            .navigationTitle("Health")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task {
                            await HealthSyncManager.shared.syncAll()
                            await viewModel.refresh()
                        }
                    } label: {
                        if syncManager.isSyncing {
                            ProgressView().tint(.green).scaleEffect(0.8)
                        } else {
                            Image(systemName: "arrow.clockwise")
                        }
                    }
                    .disabled(syncManager.isSyncing)
                    .glassEffect(in: Circle())
                }
            }
        }
        .refreshable { await viewModel.refresh() }
    }

    // MARK: - Loading

    private var loadingView: some View {
        VStack(spacing: 16) {
            Image(systemName: "heart.fill")
                .font(.system(size: 36))
                .foregroundStyle(Color(red: 0.2, green: 0.9, blue: 0.5).opacity(0.4))
                .symbolEffect(.pulse)
            Text("Syncing health data…")
                .font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Summary

    @ViewBuilder
    private func summaryView(_ s: HealthSummary) -> some View {
        ScrollView {
            VStack(spacing: 14) {
                commandHeader(summary: s)

                storyboardStrip(summary: s)

                ReadinessBanner(status: s.readiness, note: s.thorNote)

                if let dailyScore = s.dailyScore {
                    scoreStrip(dailyScore)
                }

                briefingDeck(summary: s)

                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 6) {
                        Image(systemName: "chart.bar.fill")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(Color(red: 0.2, green: 0.9, blue: 0.5))
                        Text("TODAY'S METRICS")
                            .font(.system(size: 10, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(Color(red: 0.2, green: 0.9, blue: 0.5).opacity(0.85))
                    }

                    LazyVGrid(
                        columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 2),
                        spacing: 10
                    ) {
                        MetricTile(icon: "figure.walk",
                                   label: "Steps",
                                   value: s.stepsToday.formatted(),
                                   unit: "steps",
                                   color: .white,
                                   target: Double(s.stepsToday) / 10000)
                        MetricTile(icon: "heart.fill",
                                   label: "Heart Rate",
                                   value: "\(s.heartRateAvg)",
                                   unit: "bpm",
                                   color: .red,
                                   target: heartRateTarget(s.heartRateAvg))
                        MetricTile(icon: "waveform.path.ecg",
                                   label: "HRV",
                                   value: "\(s.hrv)",
                                   unit: "ms",
                                   color: .cyan,
                                   target: Double(s.hrv) / 100)
                        MetricTile(icon: "moon.fill",
                                   label: "Sleep",
                                   value: String(format: "%.1f", s.sleepHours),
                                   unit: "hrs",
                                   color: .indigo,
                                   target: s.sleepHours / 8.0)
                        MetricTile(icon: "flame.fill",
                                   label: "Active Cal.",
                                   value: s.activeCalories.formatted(),
                                   unit: "kcal",
                                   color: .orange,
                                   target: Double(s.activeCalories) / 600)
                        MetricTile(icon: "arrow.up.circle.fill",
                                   label: "Stand Hours",
                                   value: "\(s.standHours)",
                                   unit: "/ 12",
                                   color: Color(red: 0.2, green: 0.9, blue: 0.5),
                                   target: Double(s.standHours) / 12)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(14)
                .glassEffect(in: RoundedRectangle(cornerRadius: 16))

                quickActionDock(summary: s)

                manualCheckInCard

                recentCheckinsCard

                HStack(spacing: 8) {
                    if syncManager.isSyncing {
                        ProgressView().tint(Color(red: 0.2, green: 0.9, blue: 0.5)).scaleEffect(0.7)
                        Text("Syncing to JARVIS…")
                            .font(.caption2)
                            .foregroundStyle(Color(red: 0.2, green: 0.9, blue: 0.5))
                    } else if let date = syncManager.lastSyncDate {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundStyle(Color(red: 0.2, green: 0.9, blue: 0.5))
                            .font(.caption2)
                        Text("Synced \(date.formatted(.relative(presentation: .named)))")
                            .font(.caption2).foregroundStyle(.secondary)
                        if syncManager.lastSyncedCount > 0 {
                            Text("· \(syncManager.lastSyncedCount) new")
                                .font(.caption2).foregroundStyle(.secondary)
                        }
                    } else {
                        Image(systemName: "clock").foregroundStyle(.secondary).font(.caption2)
                        Text("Last sync: \(s.lastSync)")
                            .font(.caption2).foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                .padding(.horizontal, 4)

                if let continuity = s.continuity,
                   continuity.profileFactCount > 0
                    || !continuity.guidanceLines.isEmpty
                    || !continuity.activeConditions.isEmpty
                    || !continuity.recentFirstLight.isEmpty
                    || !continuity.recentProfileFacts.isEmpty {
                    continuityCard(continuity)
                }

                if !s.readinessFactors.isEmpty {
                    readinessFactorsCard(s.readinessFactors)
                }

                if let thor = s.thorSnapshot {
                    thorCard(thor)
                }

                if let completeness = s.completeness {
                    completenessCard(completeness)
                }

                if !s.protocolItems.isEmpty {
                    guidanceCard(
                        title: "Protocol",
                        systemImage: "cross.case.fill",
                        tint: Color(red: 0.2, green: 0.9, blue: 0.5),
                        items: s.protocolItems.map { ($0.title, $0.detail, $0.emphasis == "high" ? "high" : "normal") }
                    )
                }

                if !s.alerts.isEmpty {
                    guidanceCard(
                        title: "Alerts",
                        systemImage: "exclamationmark.triangle.fill",
                        tint: .yellow,
                        items: s.alerts.map { ($0.title, $0.detail ?? "", "high") }
                    )
                }

                if !s.watchlist.isEmpty {
                    guidanceCard(
                        title: "Watchlist",
                        systemImage: "stethoscope",
                        tint: .pink,
                        items: s.watchlist.map { ($0.title, $0.detail, $0.severity == "high" ? "high" : "normal") }
                    )
                }

                if !s.nextActions.isEmpty {
                    actionListCard(s.nextActions)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    private func commandHeader(summary: HealthSummary) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("JARVIS Health Intelligence")
                        .font(.system(size: 30, weight: .bold, design: .rounded))
                        .foregroundStyle(.white)
                    Text("Personalized. Proactive. Private.")
                        .font(.caption.weight(.semibold))
                        .tracking(1.4)
                        .foregroundStyle(Color(red: 0.67, green: 0.94, blue: 0.78))
                    Text("Morning brief, vitals, coaching, and voice consultation are gathered into one live command deck without losing the real sync and recovery seams.")
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.72))
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 8) {
                    Label(summary.readiness.capitalized, systemImage: readinessBadgeSymbol(summary.readiness))
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(readinessTint(summary.readiness))
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(readinessTint(summary.readiness).opacity(0.14), in: Capsule())
                    Text(syncSummary(summary))
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.6))
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(
            LinearGradient(
                colors: [
                    Color(red: 0.08, green: 0.18, blue: 0.16),
                    Color(red: 0.04, green: 0.08, blue: 0.13)
                ],
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

    private func storyboardStrip(summary: HealthSummary) -> some View {
        let cards = [
            ("1", "Health Command", summary.readiness.capitalized + " readiness"),
            ("2", "Morning Brief", summary.dailyScore?.message ?? summary.thorNote),
            ("3", "Vitals & Trends", "\(summary.heartRateAvg)bpm · \(summary.hrv)ms HRV"),
            ("4", "Recovery Studio", summary.thorSnapshot?.thorNote ?? "Recovery posture ready"),
            ("5", "Care Command", summary.watchlist.first?.title ?? "Care lane standing by"),
            ("6", "Voice Consult", summary.nextActions.first ?? "Ask health follow-ups naturally"),
        ]

        return ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 10) {
                ForEach(cards, id: \.0) { card in
                    VStack(alignment: .leading, spacing: 8) {
                        HStack(spacing: 8) {
                            Text(card.0)
                                .font(.caption2.weight(.bold))
                                .foregroundStyle(Color(red: 0.67, green: 0.94, blue: 0.78))
                                .frame(width: 24, height: 24)
                                .background(Color.white.opacity(0.08), in: Circle())
                            Text(card.1)
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.white)
                        }
                        Text(card.2)
                            .font(.caption2)
                            .foregroundStyle(.white.opacity(0.62))
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .frame(width: 168, alignment: .leading)
                    .padding(12)
                    .background(Color.white.opacity(0.035), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 16, style: .continuous)
                            .stroke(Color.white.opacity(0.06), lineWidth: 1)
                    )
                }
            }
        }
    }

    private func briefingDeck(summary: HealthSummary) -> some View {
        HStack(alignment: .top, spacing: 12) {
            infoDeckCard(
                title: "Morning Health Brief",
                systemImage: "waveform",
                tint: Color(red: 0.36, green: 0.88, blue: 0.95),
                primary: summary.dailyScore.map { "\($0.value) \($0.grade)" } ?? summary.readiness.capitalized,
                detail: summary.dailyScore?.message ?? summary.thorNote
            )
            infoDeckCard(
                title: "Key Risk To Watch",
                systemImage: "exclamationmark.triangle.fill",
                tint: .orange,
                primary: summary.alerts.first?.title ?? summary.watchlist.first?.title ?? "No critical risk",
                detail: summary.alerts.first?.detail ?? summary.watchlist.first?.detail ?? "No acute issue surfaced in the current packet."
            )
            infoDeckCard(
                title: "Today's Recommendation",
                systemImage: "figure.walk.motion",
                tint: Color(red: 0.2, green: 0.9, blue: 0.5),
                primary: summary.nextActions.first ?? "Protect your momentum",
                detail: summary.continuity?.guidanceLines.first ?? "JARVIS is preserving the next best health move in continuity."
            )
        }
    }

    private func scoreStrip(_ score: HealthDailyScore) -> some View {
        HStack(alignment: .top, spacing: 14) {
            VStack(alignment: .leading, spacing: 4) {
                Text("DAILY SCORE")
                    .font(.system(size: 10, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(.secondary)
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text("\(score.value)")
                        .font(.system(size: 34, weight: .heavy, design: .rounded))
                        .foregroundStyle(.white)
                    Text(score.grade)
                        .font(.headline)
                        .foregroundStyle(Color(red: 0.2, green: 0.9, blue: 0.5))
                }
                if !score.message.isEmpty {
                    Text(score.message)
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.72))
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            Spacer()
            if score.estimated {
                Label("Estimated", systemImage: "wand.and.stars")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.yellow)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(.yellow.opacity(0.12), in: Capsule())
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func quickActionDock(summary: HealthSummary) -> some View {
        HStack(spacing: 10) {
            quickActionTile(
                title: "Coach",
                subtitle: summary.thorSnapshot?.readiness.replacingOccurrences(of: "_", with: " ").capitalized ?? "Recovery",
                icon: "figure.run",
                tint: .orange
            )
            quickActionTile(
                title: "Care",
                subtitle: summary.watchlist.isEmpty ? "Clear" : "\(summary.watchlist.count) watching",
                icon: "cross.case.fill",
                tint: .pink
            )
            quickActionTile(
                title: "Voice",
                subtitle: "Ask follow-ups",
                icon: "mic.fill",
                tint: .cyan
            )
        }
    }

    private var manualCheckInCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Manual Check-In", systemImage: "square.and.pencil")
                .font(.system(size: 11, weight: .bold))
                .tracking(1.0)
                .foregroundStyle(Color(red: 0.67, green: 0.94, blue: 0.78).opacity(0.95))

            TextField("Symptoms or focus", text: $checkinSymptoms)
                .textFieldStyle(.roundedBorder)

            TextField("Context note", text: $checkinNote, axis: .vertical)
                .textFieldStyle(.roundedBorder)
                .lineLimit(2...4)

            VStack(spacing: 10) {
                sliderRow("Energy", value: $checkinEnergy)
                sliderRow("Sleep", value: $checkinSleep, format: { String(format: "%.1f h", $0) })
                sliderRow("Stress", value: $checkinStress)
            }

            Button {
                Task { await submitCheckin() }
            } label: {
                HStack {
                    if isSavingCheckin {
                        ProgressView().tint(.white).scaleEffect(0.8)
                    }
                    Text(isSavingCheckin ? "Saving Check-In…" : "Save Health Check-In")
                        .font(.caption.weight(.semibold))
                }
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(Color(red: 0.2, green: 0.9, blue: 0.5).opacity(0.82), in: RoundedRectangle(cornerRadius: 14, style: .continuous))
            }
            .buttonStyle(.plain)
            .disabled(isSavingCheckin)
            .opacity(isSavingCheckin ? 0.7 : 1.0)

            Text(checkinStatusMessage)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.68))
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private var recentCheckinsCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("Recent Manual Check-Ins", systemImage: "clock.arrow.circlepath")
                    .font(.system(size: 11, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(.cyan.opacity(0.95))
                Spacer()
                if let summary = viewModel.summary, summary.manualCheckinCount > 0 {
                    Text("\(summary.manualCheckinCount)")
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(.cyan)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 5)
                        .background(.cyan.opacity(0.12), in: Capsule())
                }
            }

            if viewModel.checkins.isEmpty {
                Text("No manual check-ins recorded yet. Save one here and it will flow into the shared health continuity lane.")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.68))
                    .fixedSize(horizontal: false, vertical: true)
            } else {
                ForEach(viewModel.checkins.prefix(4)) { checkin in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(checkin.symptoms.isEmpty ? "Health check-in" : checkin.symptoms)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.white)
                        Text("Energy \(checkin.energyLevel ?? 0) · Sleep \(checkin.sleepHours ?? 0, specifier: "%.1f")h · Stress \(checkin.stressLevel ?? 0)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        if !checkin.note.isEmpty {
                            Text(checkin.note)
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.72))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(10)
                    .background(.white.opacity(0.035), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func continuityCard(_ continuity: HealthContinuity) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Carry Forward", systemImage: "heart.text.square.fill")
                .font(.system(size: 11, weight: .bold))
                .tracking(1.0)
                .foregroundStyle(Color(red: 0.2, green: 0.9, blue: 0.5).opacity(0.95))

            HStack(spacing: 10) {
                miniStat("Facts", "\(continuity.profileFactCount)", tint: .green)
                if !continuity.readinessLane.isEmpty {
                    miniStat("Lane", continuity.readinessLane.replacingOccurrences(of: "_", with: " ").capitalized, tint: .cyan)
                }
                if !continuity.activeConditions.isEmpty {
                    miniStat("Watch", "\(continuity.activeConditions.count)", tint: .pink)
                }
            }

            if !continuity.recoveryFocus.isEmpty || !continuity.subjectDisplayName.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    if !continuity.recoveryFocus.isEmpty {
                        Text("Recovery focus: \(continuity.recoveryFocus)")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.white)
                    }
                    if !continuity.subjectDisplayName.isEmpty {
                        Text("\(continuity.subjectDisplayName)'s durable health rhythm is informing today's posture.")
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.7))
                    }
                }
            }

            if !continuity.guidanceLines.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Health Rhythm")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    ForEach(continuity.guidanceLines, id: \.self) { line in
                        Text("• \(line)")
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.72))
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }

            if !continuity.activeConditions.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Active Watch")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    Text(continuity.activeConditions.joined(separator: " • "))
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.74))
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

            if !continuity.recentProfileFacts.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Durable Patterns")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    ForEach(continuity.recentProfileFacts) { fact in
                        VStack(alignment: .leading, spacing: 3) {
                            Text(fact.title)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(.white)
                            if !fact.summary.isEmpty {
                                Text(fact.summary)
                                    .font(.caption)
                                    .foregroundStyle(.white.opacity(0.72))
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                        .padding(.bottom, 2)
                    }
                }
            }

            if !continuity.recentFirstLight.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Recent First Light")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    ForEach(continuity.recentFirstLight) { moment in
                        VStack(alignment: .leading, spacing: 3) {
                            Text(moment.label)
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.white)
                            Text(moment.summary)
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.72))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func readinessFactorsCard(_ factors: [HealthReadinessFactor]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Readiness Factors", systemImage: "waveform.path.ecg.rectangle")
                .font(.system(size: 11, weight: .bold))
                .tracking(1.0)
                .foregroundStyle(.cyan.opacity(0.95))

            ForEach(factors) { factor in
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text(factor.label)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.white)
                        Spacer()
                        if factor.missing {
                            Text("Missing")
                                .font(.caption2.weight(.semibold))
                                .foregroundStyle(.yellow)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(.yellow.opacity(0.12), in: Capsule())
                        } else if let score = factor.score {
                            Text("\(score)")
                                .font(.caption.weight(.bold))
                                .foregroundStyle(.cyan)
                        }
                    }
                    HStack {
                        if let value = factor.value {
                            Text(metricValue(value, metric: factor.metric))
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.7))
                        }
                        Spacer()
                    }
                    .padding(.bottom, 2)
                }
                if factor.id != factors.last?.id {
                    Divider().opacity(0.14)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func thorCard(_ thor: HealthThorSnapshot) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Thor Movement Posture", systemImage: "figure.strengthtraining.traditional")
                .font(.system(size: 11, weight: .bold))
                .tracking(1.0)
                .foregroundStyle(.orange.opacity(0.95))

            Text(thor.thorNote)
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.82))
                .fixedSize(horizontal: false, vertical: true)

            HStack(spacing: 10) {
                miniStat("Streak", "\(thor.activityStreakDays)d", tint: .orange)
                miniStat("Week", "\(thor.totalActiveMinutesWeek)m", tint: .green)
                miniStat("Avg Steps", thor.avgDailySteps.formatted(), tint: .blue)
            }

            HStack(spacing: 8) {
                Text(thor.readiness.replacingOccurrences(of: "_", with: " ").capitalized)
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.orange)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 5)
                    .background(.orange.opacity(0.12), in: Capsule())
                if thor.needsRest {
                    Text("Recovery day suggested")
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.yellow)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 5)
                        .background(.yellow.opacity(0.12), in: Capsule())
                }
                Spacer()
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func completenessCard(_ completeness: HealthCompletenessSummary) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("Data Completeness", systemImage: "cross.case.circle.fill")
                    .font(.system(size: 11, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(.pink.opacity(0.95))
                Spacer()
                Text("\(completeness.totalScore) · \(completeness.grade)")
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(.white)
            }

            if !completeness.criticalGaps.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Critical gaps")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.pink.opacity(0.85))
                    ForEach(completeness.criticalGaps, id: \.self) { gap in
                        Text(gap)
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.74))
                    }
                }
            }

            if !completeness.quickWins.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Quick wins")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.green.opacity(0.9))
                    ForEach(completeness.quickWins, id: \.self) { item in
                        Text(item)
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.74))
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func guidanceCard(
        title: String,
        systemImage: String,
        tint: Color,
        items: [(title: String, detail: String, emphasis: String)]
    ) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Image(systemName: systemImage)
                    .foregroundStyle(tint)
                Text(title)
                    .font(.system(size: 11, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(tint.opacity(0.92))
                Spacer()
            }

            ForEach(Array(items.enumerated()), id: \.offset) { _, item in
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 8) {
                        Circle()
                            .fill(item.emphasis == "high" ? tint : .white.opacity(0.45))
                            .frame(width: 7, height: 7)
                        Text(item.title)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.white)
                    }
                    if !item.detail.isEmpty {
                        Text(item.detail)
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.68))
                            .fixedSize(horizontal: false, vertical: true)
                            .padding(.leading, 15)
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func actionListCard(_ actions: [String]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("Next Actions", systemImage: "checklist")
                .font(.system(size: 11, weight: .bold))
                .tracking(1.0)
                .foregroundStyle(.orange.opacity(0.95))
            ForEach(actions, id: \.self) { action in
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: "arrow.right.circle.fill")
                        .foregroundStyle(.orange)
                        .font(.caption)
                        .padding(.top, 2)
                    Text(action)
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.74))
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func infoDeckCard(
        title: String,
        systemImage: String,
        tint: Color,
        primary: String,
        detail: String
    ) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(title, systemImage: systemImage)
                .font(.system(size: 11, weight: .bold))
                .tracking(1.0)
                .foregroundStyle(tint.opacity(0.95))
            Text(primary)
                .font(.headline)
                .foregroundStyle(.white)
            Text(detail)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.7))
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, minHeight: 132, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 18))
    }

    private func quickActionTile(title: String, subtitle: String, icon: String, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Image(systemName: icon)
                    .foregroundStyle(tint)
                Spacer()
                Circle()
                    .fill(tint.opacity(0.22))
                    .frame(width: 9, height: 9)
            }
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.white)
            Text(subtitle)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.65))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(Color.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(Color.white.opacity(0.06), lineWidth: 1)
        )
    }

    private func readinessTint(_ status: String) -> Color {
        switch status {
        case "good":
            return Color(red: 0.2, green: 0.9, blue: 0.5)
        case "moderate":
            return .yellow
        default:
            return .red
        }
    }

    private func readinessBadgeSymbol(_ status: String) -> String {
        switch status {
        case "good":
            return "checkmark.circle.fill"
        case "moderate":
            return "minus.circle.fill"
        default:
            return "exclamationmark.triangle.fill"
        }
    }

    private func syncSummary(_ summary: HealthSummary) -> String {
        if syncManager.isSyncing {
            return "Syncing now"
        }
        if let date = syncManager.lastSyncDate {
            return "Synced \(date.formatted(.relative(presentation: .named)))"
        }
        return "Last sync \(summary.lastSync)"
    }

    private func miniStat(_ label: String, _ value: String, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label.uppercased())
                .font(.system(size: 9, weight: .bold))
                .tracking(0.8)
                .foregroundStyle(tint.opacity(0.8))
            Text(value)
                .font(.subheadline.weight(.bold))
                .foregroundStyle(.white)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
    }

    private func metricValue(_ value: Double, metric: String) -> String {
        switch metric {
        case "sleep_hours":
            return String(format: "%.1f hrs", value)
        case "hrv":
            return "\(Int(value)) ms"
        case "resting_hr":
            return "\(Int(value)) bpm"
        case "steps":
            return Int(value).formatted() + " steps"
        default:
            return String(format: "%.0f", value)
        }
    }

    private func sliderRow(_ title: String, value: Binding<Double>, format: @escaping (Double) -> String = { String(Int($0)) }) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white)
                Spacer()
                Text(format(value.wrappedValue))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Slider(value: value, in: title == "Sleep" ? 0...12 : 1...10, step: title == "Sleep" ? 0.5 : 1)
                .tint(Color(red: 0.2, green: 0.9, blue: 0.5))
        }
    }

    private func submitCheckin() async {
        isSavingCheckin = true
        checkinStatusMessage = "Saving health check-in…"
        defer { isSavingCheckin = false }
        do {
            try await viewModel.submitCheckin(
                symptoms: checkinSymptoms,
                note: checkinNote,
                energyLevel: Int(checkinEnergy.rounded()),
                sleepHours: checkinSleep,
                stressLevel: Int(checkinStress.rounded())
            )
            checkinSymptoms = ""
            checkinNote = ""
            checkinEnergy = 5
            checkinSleep = 7
            checkinStress = 4
            checkinStatusMessage = "Health check-in saved to JARVIS."
        } catch {
            checkinStatusMessage = "Unable to save check-in: \(error.localizedDescription)"
        }
    }

    // MARK: - Error

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "heart.slash.fill")
                .font(.system(size: 44)).foregroundStyle(.secondary)
            Text("Health data unavailable")
                .font(.headline).foregroundStyle(.white)
            Text(message)
                .font(.caption).foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Try Again") { Task { await viewModel.refresh() } }
                .buttonStyle(.borderedProminent)
                .tint(Color(red: 0.2, green: 0.9, blue: 0.5))
        }
        .padding(24)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func heartRateTarget(_ bpm: Int) -> Double {
        // 50–100 bpm is healthy; map to 0–1 (peak at 70)
        Double(bpm).clamped(to: 40...120).interpolated(from: 40...120, to: 0...1)
    }
}

// MARK: - Readiness banner

private struct ReadinessBanner: View {
    let status: String
    let note: String

    var statusColor: Color {
        switch status { case "good": Color(red: 0.2, green: 0.9, blue: 0.5); case "moderate": .yellow; default: .red }
    }
    var statusIcon: String {
        switch status { case "good": "checkmark.seal.fill"; case "moderate": "minus.circle.fill"; default: "exclamationmark.triangle.fill" }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 14) {
                // Score ring placeholder
                ZStack {
                    Circle()
                        .stroke(statusColor.opacity(0.18), lineWidth: 6)
                        .frame(width: 56, height: 56)
                    Circle()
                        .trim(from: 0, to: readinessScore)
                        .stroke(statusColor, style: StrokeStyle(lineWidth: 6, lineCap: .round))
                        .frame(width: 56, height: 56)
                        .rotationEffect(.degrees(-90))
                    Image(systemName: statusIcon)
                        .font(.system(size: 18))
                        .foregroundStyle(statusColor)
                }

                VStack(alignment: .leading, spacing: 3) {
                    Text("READINESS")
                        .font(.system(size: 9, weight: .bold))
                        .tracking(1.2)
                        .foregroundStyle(.secondary)
                    Text(status.capitalized)
                        .font(.title2.bold())
                        .foregroundStyle(statusColor)
                }
                Spacer()
            }

            if !note.isEmpty {
                Text(note)
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.7))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(16)
        .background(
            ZStack {
                RoundedRectangle(cornerRadius: 16)
                    .fill(statusColor.opacity(0.07))
            }
        )
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private var readinessScore: Double {
        switch status { case "good": 0.85; case "moderate": 0.55; default: 0.25 }
    }
}

// MARK: - Metric tile

private struct MetricTile: View {
    let icon:   String
    let label:  String
    let value:  String
    let unit:   String
    let color:  Color
    let target: Double   // 0–1 for the progress bar

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: icon)
                    .font(.system(size: 13))
                    .foregroundStyle(color)
                Spacer()
                // Thin progress bar
                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Capsule().fill(color.opacity(0.12)).frame(height: 3)
                        Capsule()
                            .fill(color)
                            .frame(width: geo.size.width * min(target, 1.0), height: 3)
                    }
                }
                .frame(width: 36, height: 3)
            }

            Text(value)
                .font(.system(size: 22, weight: .bold).monospacedDigit())
                .foregroundStyle(.white)
                .lineLimit(1)
                .minimumScaleFactor(0.7)

            HStack(spacing: 3) {
                Text(label).font(.caption2).foregroundStyle(.secondary)
                Text("·").font(.caption2).foregroundStyle(.secondary)
                Text(unit).font(.caption2).foregroundStyle(color.opacity(0.7))
            }
        }
        .padding(12)
        .glassEffect(in: RoundedRectangle(cornerRadius: 14))
    }
}

// MARK: - Double helpers

private extension Double {
    func clamped(to range: ClosedRange<Double>) -> Double {
        max(range.lowerBound, min(range.upperBound, self))
    }
    func interpolated(from input: ClosedRange<Double>, to output: ClosedRange<Double>) -> Double {
        let t = (self - input.lowerBound) / (input.upperBound - input.lowerBound)
        return output.lowerBound + t * (output.upperBound - output.lowerBound)
    }
}

#Preview {
    HealthView(viewModel: HealthViewModel())
}
