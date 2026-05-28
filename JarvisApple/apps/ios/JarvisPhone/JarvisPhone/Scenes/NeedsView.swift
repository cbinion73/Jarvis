import SwiftUI
import JarvisKit

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
                    Button {
                        Task { await viewModel.refresh() }
                    } label: {
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
            ProgressView()
                .tint(.cyan)
                .scaleEffect(1.4)
            Text("Checking for requests…")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - List

    private var itemList: some View {
        ScrollView {
            VStack(spacing: 12) {
                ForEach(viewModel.items) { item in
                    NeedsItemCard(item: item) {
                        Task { await viewModel.approve(item: item) }
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    // MARK: - Empty state

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 56))
                .foregroundStyle(.green)
            Text("All clear")
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

// MARK: - NeedsItemCard

private struct NeedsItemCard: View {
    let item: NeedsItem
    let onApprove: () -> Void

    @State private var confirming = false

    var riskColor: Color {
        switch item.risk {
        case "high":   return .red
        case "medium": return .orange
        default:       return .yellow
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {

            // Header row
            HStack(alignment: .firstTextBaseline) {
                Label(item.risk.capitalized, systemImage: riskIcon)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(riskColor)
                Spacer()
                Text(item.agent)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            // Body text
            Text(item.text)
                .font(.subheadline)
                .foregroundStyle(.white)
                .fixedSize(horizontal: false, vertical: true)

            // Expiry
            if let exp = item.expiresIn {
                Label(exp, systemImage: "clock")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            // Approve button
            Button(action: { confirming = true }) {
                Label("Approve", systemImage: "checkmark.shield.fill")
                    .frame(maxWidth: .infinity)
                    .font(.subheadline.weight(.semibold))
            }
            .buttonStyle(.borderedProminent)
            .tint(.green)
            .confirmationDialog("Approve this request?", isPresented: $confirming, titleVisibility: .visible) {
                Button("Approve", role: .none, action: onApprove)
                Button("Cancel", role: .cancel) {}
            } message: {
                Text(item.text)
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private var riskIcon: String {
        switch item.risk {
        case "high":   return "exclamationmark.triangle.fill"
        case "medium": return "exclamationmark.circle.fill"
        default:       return "info.circle.fill"
        }
    }
}

#Preview {
    NeedsView(viewModel: NeedsViewModel())
}
