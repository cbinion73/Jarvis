import SwiftUI

struct NeedsWatchView: View {

    @EnvironmentObject var vm: WatchViewModel

    var body: some View {
        Group {
            if vm.needsItems.isEmpty {
                VStack(spacing: 10) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 32))
                        .foregroundStyle(.green)
                    Text("All clear")
                        .font(.headline)
                        .foregroundStyle(.white)
                    Text("Nothing needs you.")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    VStack(spacing: 8) {
                        ForEach(Array(vm.needsItems.enumerated()), id: \.offset) { _, item in
                            NeedsWatchRow(item: item)
                        }
                    }
                    .padding()
                }
            }
        }
        .navigationTitle("Needs")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - Row

private struct NeedsWatchRow: View {
    let item: [String: String]

    var riskColor: Color {
        switch item["risk"] {
        case "high":   return .red
        case "medium": return .orange
        default:       return .yellow
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 5) {
                Circle()
                    .fill(riskColor)
                    .frame(width: 6, height: 6)
                Text(item["agent"] ?? "JARVIS")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Text(item["text"] ?? "")
                .font(.caption)
                .foregroundStyle(.white)
                .fixedSize(horizontal: false, vertical: true)
            if let exp = item["expires_in"] {
                Text(exp)
                    .font(.caption2)
                    .foregroundStyle(riskColor.opacity(0.8))
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(riskColor.opacity(0.12))
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .strokeBorder(riskColor.opacity(0.3), lineWidth: 0.5)
        )
    }
}
