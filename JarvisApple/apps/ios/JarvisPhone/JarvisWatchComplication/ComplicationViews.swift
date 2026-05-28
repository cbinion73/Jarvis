import SwiftUI
import WidgetKit

// MARK: - Circular (corner of watch face)

struct CircularComplicationView: View {
    let entry: JarvisEntry

    var body: some View {
        ZStack {
            Circle().fill(.cyan.opacity(0.2))
            VStack(spacing: 1) {
                Image(systemName: "brain.head.profile")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(.cyan)
                if entry.needsCount > 0 {
                    Text("\(entry.needsCount)")
                        .font(.system(size: 10, weight: .bold).monospacedDigit())
                        .foregroundColor(.orange)
                }
            }
        }
    }
}

// MARK: - Rectangular (wide band at bottom of watch face)

struct RectangularComplicationView: View {
    let entry: JarvisEntry

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "brain.head.profile")
                .foregroundColor(.cyan)
                .font(.caption.weight(.semibold))

            VStack(alignment: .leading, spacing: 1) {
                Text("JARVIS · \(entry.mode.capitalized)")
                    .font(.caption2.weight(.semibold))
                    .foregroundColor(.cyan)
                if entry.needsCount > 0 {
                    Text("\(entry.needsCount) need\(entry.needsCount == 1 ? "s" : "") your approval")
                        .font(.caption2)
                        .foregroundColor(.orange)
                } else {
                    Text("All clear")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }
            Spacer()
        }
    }
}

// MARK: - Inline (top bar of watch face)

struct InlineComplicationView: View {
    let entry: JarvisEntry

    var body: some View {
        if entry.needsCount > 0 {
            Label("JARVIS · \(entry.needsCount) needs", systemImage: "exclamationmark.circle.fill")
        } else {
            Label("JARVIS · \(entry.mode)", systemImage: "brain.head.profile")
        }
    }
}

// MARK: - Corner (corner gauge / image)

struct CornerComplicationView: View {
    let entry: JarvisEntry

    var body: some View {
        ZStack {
            Image(systemName: "brain.head.profile")
                .foregroundColor(.cyan)
            if entry.needsCount > 0 {
                Text("\(entry.needsCount)")
                    .font(.system(size: 8, weight: .bold))
                    .foregroundColor(.white)
                    .padding(3)
                    .background(Color.orange)
                    .clipShape(Circle())
                    .offset(x: 8, y: -8)
            }
        }
    }
}
