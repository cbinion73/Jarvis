import SwiftUI
import JarvisKit

// MARK: - HealthView  "Vitals Monitor"

struct HealthView: View {

    @ObservedObject var viewModel: HealthViewModel
    @ObservedObject private var syncManager = HealthSyncManager.shared

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

                // ── Readiness gradient banner ──────────────────────
                ReadinessBanner(status: s.readiness, note: s.thorNote)

                if let dailyScore = s.dailyScore {
                    scoreStrip(dailyScore)
                }

                // ── Metrics 2-column grid ──────────────────────────
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

                // ── Sync status ────────────────────────────────────
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

                if !s.nextActions.isEmpty {
                    actionListCard(s.nextActions)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
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
