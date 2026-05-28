import SwiftUI

struct BriefingWatchView: View {

    @EnvironmentObject var vm: WatchViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {

                // ── Greeting ──────────────────────────────────────
                VStack(alignment: .leading, spacing: 2) {
                    Text(vm.greeting)
                        .font(.headline)
                        .foregroundStyle(.cyan)
                    Text(vm.mode.capitalized)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }

                // ── Needs alert chip ──────────────────────────────
                if vm.needsCount > 0 {
                    Label("\(vm.needsCount) need\(vm.needsCount == 1 ? "s" : "") you",
                          systemImage: "exclamationmark.circle.fill")
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.orange)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.orange.opacity(0.2))
                        .clipShape(Capsule())
                }

                // ── Top 3 items ───────────────────────────────────
                if vm.briefTop3.isEmpty {
                    Text("No brief yet — refresh to sync")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .italic()
                } else {
                    VStack(alignment: .leading, spacing: 6) {
                        ForEach(Array(vm.briefTop3.enumerated()), id: \.offset) { _, item in
                            HStack(alignment: .top, spacing: 6) {
                                Circle()
                                    .fill(item["priority"] == "high" ? Color.orange : Color.cyan)
                                    .frame(width: 5, height: 5)
                                    .padding(.top, 4)
                                Text(item["text"] ?? "")
                                    .font(.caption)
                                    .foregroundStyle(.white)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.white.opacity(0.08))
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                }

                // ── Last update ───────────────────────────────────
                if let update = vm.lastUpdate {
                    Text(update.formatted(.relative(presentation: .named)))
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }

                // ── Refresh ───────────────────────────────────────
                Button {
                    vm.requestRefresh()
                } label: {
                    if vm.isRefreshing {
                        ProgressView().tint(.cyan)
                    } else {
                        Label("Refresh", systemImage: "arrow.clockwise")
                            .font(.caption2)
                    }
                }
                .buttonStyle(.bordered)
                .tint(.cyan)
                .frame(maxWidth: .infinity)
            }
            .padding()
        }
        .navigationTitle("Brief")
        .navigationBarTitleDisplayMode(.inline)
    }
}
