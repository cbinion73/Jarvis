import ActivityKit
import WidgetKit
import SwiftUI
import JarvisKit

// MARK: - Live Activity Widget (Dynamic Island + Lock Screen)

struct JarvisLiveActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: JarvisActivityAttributes.self) { context in
            // ── Lock Screen banner ─────────────────────────────────────
            LockScreenLiveActivityView(context: context)
        } dynamicIsland: { context in
            DynamicIsland {
                // ── Expanded (long press) ──────────────────────────────
                DynamicIslandExpandedRegion(.leading) {
                    HStack(spacing: 6) {
                        Image(systemName: modeIcon(context.state.mode))
                            .foregroundStyle(.cyan)
                            .font(.caption)
                        Text(modeName(context.state.mode))
                            .font(.caption2)
                            .foregroundStyle(.cyan)
                    }
                }
                DynamicIslandExpandedRegion(.trailing) {
                    if context.state.needsCount > 0 {
                        Label("\(context.state.needsCount)", systemImage: "exclamationmark.circle.fill")
                            .font(.caption2.bold())
                            .foregroundStyle(.orange)
                    }
                }
                DynamicIslandExpandedRegion(.center) {
                    VStack(spacing: 2) {
                        if !context.state.agentName.isEmpty {
                            Text(context.state.agentName)
                                .font(.caption.bold())
                                .foregroundStyle(.white)
                        }
                        Text(context.state.action)
                            .font(.caption2)
                            .foregroundStyle(.white.opacity(0.75))
                            .lineLimit(2)
                            .multilineTextAlignment(.center)
                    }
                }
                DynamicIslandExpandedRegion(.bottom) {
                    Text(context.state.statusLine)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity)
                        .padding(.bottom, 4)
                }
            } compactLeading: {
                // ── Compact leading (small pill) ───────────────────────
                Image(systemName: "j.circle.fill")
                    .foregroundStyle(.cyan)
                    .font(.caption)
            } compactTrailing: {
                // ── Compact trailing ───────────────────────────────────
                if context.state.needsCount > 0 {
                    Text("\(context.state.needsCount)")
                        .font(.caption2.bold())
                        .foregroundStyle(.orange)
                } else {
                    Image(systemName: agentIcon(context.state.agentName))
                        .foregroundStyle(.white.opacity(0.7))
                        .font(.caption2)
                }
            } minimal: {
                // ── Minimal (when another app owns the island) ─────────
                Image(systemName: context.state.needsCount > 0
                      ? "exclamationmark.circle.fill" : "j.circle.fill")
                    .foregroundStyle(context.state.needsCount > 0 ? .orange : .cyan)
                    .font(.caption2)
            }
        }
    }
}

// MARK: - Lock Screen view

private struct LockScreenLiveActivityView: View {
    let context: ActivityViewContext<JarvisActivityAttributes>

    var body: some View {
        HStack(spacing: 12) {
            // JARVIS indicator
            ZStack {
                Circle()
                    .fill(.cyan.opacity(0.15))
                    .frame(width: 44, height: 44)
                Image(systemName: modeIcon(context.state.mode))
                    .foregroundStyle(.cyan)
                    .font(.title3)
            }

            VStack(alignment: .leading, spacing: 2) {
                if !context.state.agentName.isEmpty {
                    Text(context.state.agentName)
                        .font(.caption.bold())
                        .foregroundStyle(.primary)
                }
                Text(context.state.action)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            Spacer()

            if context.state.needsCount > 0 {
                VStack(spacing: 2) {
                    Text("\(context.state.needsCount)")
                        .font(.title3.bold())
                        .foregroundStyle(.orange)
                    Text("need\(context.state.needsCount == 1 ? "s" : "")\nyou")
                        .font(.caption2)
                        .foregroundStyle(.orange.opacity(0.8))
                        .multilineTextAlignment(.center)
                }
            }
        }
        .padding(16)
        .background(.black.opacity(0.001)) // ensures full-width hit area
    }
}

// MARK: - Helpers

private func modeIcon(_ mode: String) -> String {
    switch mode {
    case "morning_brief": return "sun.horizon.fill"
    case "lunch_brief":   return "sun.max.fill"
    case "daily_recap":   return "moon.stars.fill"
    default:              return "j.circle.fill"
    }
}

private func modeName(_ mode: String) -> String {
    switch mode {
    case "morning_brief": return "Morning"
    case "lunch_brief":   return "Midday"
    case "daily_recap":   return "Evening"
    default:              return "JARVIS"
    }
}

private func agentIcon(_ name: String) -> String {
    switch name.lowercased() {
    case "friday":   return "envelope.fill"
    case "thor":     return "cloud.bolt.fill"
    case "coulson":  return "calendar"
    case "vision":   return "eye.fill"
    default:         return "gearshape.fill"
    }
}
