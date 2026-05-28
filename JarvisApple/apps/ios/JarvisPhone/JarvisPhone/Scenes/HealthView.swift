import SwiftUI
import JarvisKit

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
                            ProgressView()
                                .tint(.cyan)
                                .scaleEffect(0.8)
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
            ProgressView()
                .tint(.cyan)
                .scaleEffect(1.4)
            Text("Syncing health data…")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Summary

    @ViewBuilder
    private func summaryView(_ s: HealthSummary) -> some View {
        ScrollView {
            VStack(spacing: 14) {

                // ── Readiness banner ──────────────────────────────
                HStack(spacing: 16) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Readiness")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.secondary)
                        Text(s.readiness.capitalized)
                            .font(.title2.bold())
                            .foregroundStyle(readinessColor(s.readiness))
                        if !s.thorNote.isEmpty {
                            Text(s.thorNote)
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.75))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    Spacer()
                    readinessIcon(s.readiness)
                        .font(.system(size: 44))
                        .foregroundStyle(readinessColor(s.readiness))
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
                .glassEffect(in: RoundedRectangle(cornerRadius: 16))

                // ── Today's Metrics ───────────────────────────────
                GlassHealthSection(title: "Today's Metrics", icon: "chart.bar.fill") {
                    HealthMetricRow(icon: "figure.walk",          label: "Steps",
                                   value: "\(s.stepsToday.formatted())", unit: "steps")
                    Divider().opacity(0.3)
                    HealthMetricRow(icon: "heart.fill",           label: "Heart Rate",
                                   value: "\(s.heartRateAvg)",   unit: "bpm",  iconColor: .red)
                    Divider().opacity(0.3)
                    HealthMetricRow(icon: "waveform.path.ecg",   label: "HRV",
                                   value: "\(s.hrv)",             unit: "ms",   iconColor: .cyan)
                    Divider().opacity(0.3)
                    HealthMetricRow(icon: "moon.fill",            label: "Sleep",
                                   value: String(format: "%.1f", s.sleepHours), unit: "hrs", iconColor: .indigo)
                    Divider().opacity(0.3)
                    HealthMetricRow(icon: "flame.fill",           label: "Active Cal.",
                                   value: "\(s.activeCalories.formatted())", unit: "kcal", iconColor: .orange)
                    Divider().opacity(0.3)
                    HealthMetricRow(icon: "arrow.up.circle.fill", label: "Stand Hours",
                                   value: "\(s.standHours)",     unit: "/ 12", iconColor: .green)
                }

                // ── Sync status ───────────────────────────────────
                HStack(spacing: 8) {
                    if syncManager.isSyncing {
                        ProgressView().tint(.cyan).scaleEffect(0.7)
                        Text("Syncing to JARVIS…")
                            .font(.caption2)
                            .foregroundStyle(.cyan)
                    } else if let date = syncManager.lastSyncDate {
                        Image(systemName: "checkmark.circle.fill").foregroundStyle(.green).font(.caption2)
                        VStack(alignment: .leading, spacing: 1) {
                            Text("Pushed to JARVIS \(date.formatted(.relative(presentation: .named)))")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                            if syncManager.lastSyncedCount > 0 {
                                Text("\(syncManager.lastSyncedCount) new samples")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    } else {
                        Image(systemName: "clock").foregroundStyle(.secondary).font(.caption2)
                        Text("Last sync: \(s.lastSync)")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                .padding(.horizontal, 4)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    // MARK: - Error

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "heart.slash.fill")
                .font(.system(size: 44))
                .foregroundStyle(.secondary)
            Text("Health data unavailable")
                .font(.headline)
                .foregroundStyle(.white)
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Try Again") {
                Task { await viewModel.refresh() }
            }
            .buttonStyle(.borderedProminent)
            .tint(.cyan)
        }
        .padding(24)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Helpers

    private func readinessColor(_ r: String) -> Color {
        switch r {
        case "good":     return .green
        case "moderate": return .yellow
        default:         return .red
        }
    }

    private func readinessIcon(_ r: String) -> Image {
        switch r {
        case "good":     return Image(systemName: "checkmark.seal.fill")
        case "moderate": return Image(systemName: "minus.circle.fill")
        default:         return Image(systemName: "exclamationmark.triangle.fill")
        }
    }
}

// MARK: - Glass section wrapper

private struct GlassHealthSection<Content: View>: View {
    let title: String
    let icon: String
    var accentColor: Color = .cyan
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(title, systemImage: icon)
                .font(.caption.weight(.semibold))
                .foregroundStyle(accentColor)
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - HealthMetricRow

private struct HealthMetricRow: View {
    let icon: String
    let label: String
    let value: String
    let unit: String
    var iconColor: Color = .cyan

    var body: some View {
        HStack {
            Image(systemName: icon)
                .foregroundStyle(iconColor)
                .frame(width: 24)
            Text(label)
                .font(.subheadline)
                .foregroundStyle(.white)
            Spacer()
            Text(value)
                .font(.subheadline.monospacedDigit().bold())
                .foregroundStyle(.white)
            Text(unit)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 2)
    }
}

#Preview {
    HealthView(viewModel: HealthViewModel())
}
