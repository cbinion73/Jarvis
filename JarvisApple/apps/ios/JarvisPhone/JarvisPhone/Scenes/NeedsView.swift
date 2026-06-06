import SwiftUI
import JarvisKit

// MARK: - NeedsView  "Alert Center"

struct NeedsView: View {

    @ObservedObject var viewModel: NeedsViewModel

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                Group {
                    if viewModel.isLoading && viewModel.items.isEmpty {
                        loadingView
                    } else if viewModel.items.isEmpty {
                        emptyState
                    } else {
                        itemList
                    }
                }
            }
            .navigationTitle("Needs You")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { Task { await viewModel.refresh() } } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .glassEffect(in: Circle())
                }
            }
            .alert("Error", isPresented: Binding(
                get: { viewModel.errorMessage != nil },
                set: { if !$0 { viewModel.errorMessage = nil } }
            )) {
                Button("OK", role: .cancel) { viewModel.errorMessage = nil }
            } message: {
                Text(viewModel.errorMessage ?? "")
            }
        }
        .refreshable { await viewModel.refresh() }
    }

    // MARK: - Loading

    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView().tint(.red).scaleEffect(1.4)
            Text("Checking for requests…")
                .font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - List

    private var itemList: some View {
        ScrollView {
            VStack(spacing: 12) {
                // Waiting count banner
                HStack(spacing: 10) {
                    Image(systemName: "exclamationmark.circle.fill")
                        .foregroundStyle(.red)
                        .font(.title3)
                    VStack(alignment: .leading, spacing: 1) {
                        Text("\(viewModel.items.count) WAITING")
                            .font(.system(size: 11, weight: .black))
                            .tracking(1.2)
                            .foregroundStyle(.red)
                        Text("Decisions required from you")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .glassEffect(in: RoundedRectangle(cornerRadius: 12))

                HStack(spacing: 10) {
                    needsMetric("High Risk", "\(viewModel.items.filter { $0.risk == "high" }.count)")
                    needsMetric("Confirm", "\(viewModel.items.filter { $0.requiresConfirmation == true }.count)")
                    needsMetric("Expiring", "\(viewModel.items.filter { ($0.expiresIn ?? "").localizedCaseInsensitiveContains("min") }.count)")
                }

                if let lastActionMessage = viewModel.lastActionMessage, !lastActionMessage.isEmpty {
                    HStack(spacing: 8) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundStyle(.green)
                        Text(lastActionMessage)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white)
                        Spacer()
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .glassEffect(in: RoundedRectangle(cornerRadius: 12))
                }

                ForEach(viewModel.items) { item in
                    AlertItemCard(item: item) {
                        Task { await viewModel.approve(item: item) }
                    } onReject: {
                        Task { await viewModel.reject(item: item) }
                    } onCancel: {
                        Task { await viewModel.cancel(item: item) }
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    private func needsMetric(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .glassEffect(in: RoundedRectangle(cornerRadius: 12))
    }

    // MARK: - Empty

    private var emptyState: some View {
        VStack(spacing: 20) {
            ZStack {
                Circle()
                    .fill(Color.green.opacity(0.1))
                    .frame(width: 90, height: 90)
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 52))
                    .foregroundStyle(.green)
            }
            Text("All Clear")
                .font(.title2.bold())
                .foregroundStyle(.white)
            Text("No approvals or decisions waiting.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding(32)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Alert item card

private struct AlertItemCard: View {
    let item:      NeedsItem
    let onApprove: () -> Void
    let onReject: () -> Void
    let onCancel: () -> Void

    @State private var confirming = false
    @State private var confirmReject = false
    @State private var confirmCancel = false

    var riskColor: Color {
        switch item.risk { case "high": .red; case "medium": .orange; default: .yellow }
    }

    var riskBorderWidth: CGFloat {
        switch item.risk { case "high": 4; case "medium": 3; default: 2 }
    }

    var riskIcon: String {
        switch item.risk {
        case "high":   return "exclamationmark.triangle.fill"
        case "medium": return "exclamationmark.circle.fill"
        default:       return "info.circle.fill"
        }
    }

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            // Left risk strip
            RoundedRectangle(cornerRadius: 2)
                .fill(riskColor)
                .frame(width: riskBorderWidth)
                .padding(.vertical, 1)

            VStack(alignment: .leading, spacing: 12) {
                // Header
                HStack(alignment: .firstTextBaseline) {
                    Label(item.risk.capitalized, systemImage: riskIcon)
                        .font(.caption.weight(.bold))
                        .foregroundStyle(riskColor)
                    Spacer()
                    Text(item.agent)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }

                // Body
                Text(item.text)
                    .font(.subheadline)
                    .foregroundStyle(.white)
                    .fixedSize(horizontal: false, vertical: true)

                if let detail = item.detail, !detail.isEmpty {
                    Text(detail)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                if let targetSummary = item.targetSummary, !targetSummary.isEmpty {
                    Label(targetSummary, systemImage: "scope")
                        .font(.caption2)
                        .foregroundStyle(.white.opacity(0.9))
                }

                HStack(spacing: 8) {
                    if let exp = item.expiresIn {
                        Label(exp, systemImage: "clock")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }

                    if let createdAt = item.createdAt, !createdAt.isEmpty {
                        Label(relativeDate(createdAt), systemImage: "calendar")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }

                HStack(spacing: 8) {
                    if let requestType = item.requestType, !requestType.isEmpty {
                        Text(requestType.replacingOccurrences(of: "_", with: " ").capitalized)
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(riskColor.opacity(0.9))
                    }
                    if let priority = item.priority {
                        Text("P\(priority)")
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(.secondary)
                    }
                    if let status = item.status, !status.isEmpty {
                        Text(status.capitalized)
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(.secondary)
                    }
                }

                if let confirmationPhrase = item.confirmationPhrase,
                   item.requiresConfirmation == true,
                   !confirmationPhrase.isEmpty {
                    Text("Requires confirmation phrase: \(confirmationPhrase)")
                        .font(.caption2)
                        .foregroundStyle(.orange.opacity(0.9))
                        .fixedSize(horizontal: false, vertical: true)
                }

                if !item.tags.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 6) {
                            ForEach(item.tags, id: \.self) { tag in
                                Text(tag)
                                    .font(.caption2.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(.white.opacity(0.07), in: Capsule())
                            }
                        }
                    }
                }

                if !item.contextLines.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(item.contextLines, id: \.self) { line in
                            Text(line)
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }

                HStack(spacing: 8) {
                    if item.allowedActions.contains("approve") {
                        Button(action: { confirming = true }) {
                            HStack(spacing: 6) {
                                Image(systemName: "checkmark.shield.fill")
                                Text("Approve Now")
                                    .fontWeight(.semibold)
                            }
                            .frame(maxWidth: .infinity)
                            .font(.subheadline)
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(.green)
                        .confirmationDialog("Approve this request?", isPresented: $confirming, titleVisibility: .visible) {
                            Button("Approve", role: .none, action: onApprove)
                            Button("Cancel", role: .cancel) {}
                        } message: { Text(item.text) }
                    }

                    if item.allowedActions.contains("reject") {
                        Button("Send Back", role: .destructive) { confirmReject = true }
                            .buttonStyle(.bordered)
                            .confirmationDialog("Reject this request?", isPresented: $confirmReject, titleVisibility: .visible) {
                                Button("Reject", role: .destructive, action: onReject)
                                Button("Keep Pending", role: .cancel) {}
                            } message: { Text(item.text) }
                    }

                    if item.allowedActions.contains("cancel") {
                        Button("Cancel Request") { confirmCancel = true }
                            .buttonStyle(.bordered)
                            .confirmationDialog("Cancel this request?", isPresented: $confirmCancel, titleVisibility: .visible) {
                                Button("Cancel Request", role: .destructive, action: onCancel)
                                Button("Keep Pending", role: .cancel) {}
                            } message: { Text(item.text) }
                    }
                }

                if item.allowedActions.contains("reject") || item.allowedActions.contains("cancel") {
                    Text("Alternate actions let you decline the move or clear it from the queue without approving execution.")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .padding(14)
        }
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
        // Very subtle risk-colored background tint for high items
        .background(
            item.risk == "high"
                ? riskColor.opacity(0.04).clipShape(RoundedRectangle(cornerRadius: 16))
                : nil
        )
    }

    private func relativeDate(_ isoString: String) -> String {
        let formatter = ISO8601DateFormatter()
        guard let date = formatter.date(from: isoString) else { return isoString }
        return date.formatted(date: .abbreviated, time: .shortened)
    }
}

#Preview {
    NeedsView(viewModel: NeedsViewModel())
}
