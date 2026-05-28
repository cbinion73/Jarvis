import WidgetKit
import SwiftUI

// MARK: - Timeline Provider

struct JarvisTimelineProvider: TimelineProvider {
    func placeholder(in context: Context) -> JarvisEntry {
        JarvisEntry.placeholder
    }

    func getSnapshot(in context: Context, completion: @escaping (JarvisEntry) -> Void) {
        completion(JarvisEntry(snapshot: JarvisSnapshot.load()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<JarvisEntry>) -> Void) {
        let entry = JarvisEntry(snapshot: JarvisSnapshot.load())
        // Refresh every 15 minutes
        let next = Calendar.current.date(byAdding: .minute, value: 15, to: Date())!
        completion(Timeline(entries: [entry], policy: .after(next)))
    }
}

// MARK: - Entry

struct JarvisEntry: TimelineEntry {
    let date        = Date()
    let greeting:    String
    let mode:        String
    let needsCount:  Int
    let briefItems:  [[String: String]]
    let weatherTemp: String
    let weatherCond: String
    let agentAction: String

    init(snapshot s: JarvisSnapshot) {
        greeting    = s.greeting
        mode        = s.mode
        needsCount  = s.needsCount
        briefItems  = s.briefItems
        weatherTemp = s.weatherTemp
        weatherCond = s.weatherCond
        agentAction = s.agentAction
    }

    static let placeholder = JarvisEntry(snapshot: JarvisSnapshot(
        greeting: "Good morning, Sir.",
        mode: "morning_brief",
        needsCount: 2,
        briefItems: [
            ["text": "3 emails need replies", "priority": "high"],
            ["text": "Team standup in 20 min", "priority": "normal"],
            ["text": "Weather: Clear, 72°", "priority": "normal"],
        ],
        weatherTemp: "72°",
        weatherCond: "Clear",
        weatherKey: "clear_day",
        agentName: "FRIDAY",
        agentAction: "Processing emails…",
        lastUpdated: Date()
    ))
}

// MARK: - Small Widget

struct JarvisSmallWidget: Widget {
    let kind = "JarvisSmallWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: JarvisTimelineProvider()) { entry in
            SmallWidgetView(entry: entry)
                .containerBackground(.black, for: .widget)
        }
        .configurationDisplayName("JARVIS Status")
        .description("Quick JARVIS status at a glance.")
        .supportedFamilies([.systemSmall])
    }
}

private struct SmallWidgetView: View {
    let entry: JarvisEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: modeIcon(entry.mode))
                    .foregroundStyle(.cyan)
                    .font(.caption)
                Spacer()
                if entry.needsCount > 0 {
                    Text("\(entry.needsCount)")
                        .font(.caption2.bold())
                        .foregroundStyle(.white)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(.orange)
                        .clipShape(Capsule())
                }
            }

            Spacer()

            Text(entry.weatherTemp)
                .font(.title.bold())
                .foregroundStyle(.white)
            Text(entry.weatherCond)
                .font(.caption2)
                .foregroundStyle(.secondary)

            Spacer()

            Text(modeLabel(entry.mode))
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.cyan.opacity(0.8))
        }
        .padding(12)
    }
}

// MARK: - Medium Widget

struct JarvisMediumWidget: Widget {
    let kind = "JarvisMediumWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: JarvisTimelineProvider()) { entry in
            MediumWidgetView(entry: entry)
                .containerBackground(.black, for: .widget)
        }
        .configurationDisplayName("JARVIS Brief")
        .description("Your morning brief at a glance.")
        .supportedFamilies([.systemMedium])
    }
}

private struct MediumWidgetView: View {
    let entry: JarvisEntry

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Left column — weather + mode
            VStack(alignment: .leading, spacing: 4) {
                Image(systemName: modeIcon(entry.mode))
                    .foregroundStyle(.cyan)
                    .font(.title2)
                Text(entry.weatherTemp)
                    .font(.title.bold())
                    .foregroundStyle(.white)
                Text(entry.weatherCond)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Spacer()
                if entry.needsCount > 0 {
                    Label("\(entry.needsCount)", systemImage: "exclamationmark.circle.fill")
                        .font(.caption2.bold())
                        .foregroundStyle(.orange)
                }
            }
            .frame(width: 70)

            Divider().background(.white.opacity(0.2))

            // Right column — brief items
            VStack(alignment: .leading, spacing: 5) {
                Text(modeLabel(entry.mode))
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.cyan.opacity(0.8))

                ForEach(Array(entry.briefItems.prefix(3).enumerated()), id: \.offset) { _, item in
                    HStack(alignment: .top, spacing: 5) {
                        Circle()
                            .fill(item["priority"] == "high" ? Color.orange : Color.cyan)
                            .frame(width: 4, height: 4)
                            .padding(.top, 4)
                        Text(item["text"] ?? "")
                            .font(.caption2)
                            .foregroundStyle(.white.opacity(0.85))
                            .lineLimit(2)
                    }
                }

                if entry.briefItems.isEmpty {
                    Text("No items yet")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(14)
    }
}

// MARK: - Large Widget

struct JarvisLargeWidget: Widget {
    let kind = "JarvisLargeWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: JarvisTimelineProvider()) { entry in
            LargeWidgetView(entry: entry)
                .containerBackground(.black, for: .widget)
        }
        .configurationDisplayName("JARVIS Console")
        .description("Full JARVIS briefing console.")
        .supportedFamilies([.systemLarge])
    }
}

private struct LargeWidgetView: View {
    let entry: JarvisEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            // Header
            HStack {
                Image(systemName: modeIcon(entry.mode))
                    .foregroundStyle(.cyan)
                VStack(alignment: .leading, spacing: 1) {
                    Text("JARVIS")
                        .font(.caption.bold())
                        .foregroundStyle(.cyan)
                    Text(modeLabel(entry.mode))
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 1) {
                    Text(entry.weatherTemp)
                        .font(.subheadline.bold())
                        .foregroundStyle(.white)
                    Text(entry.weatherCond)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }

            Divider().background(.white.opacity(0.15))

            // Brief items
            Text(entry.greeting)
                .font(.caption.bold())
                .foregroundStyle(.white)

            VStack(alignment: .leading, spacing: 6) {
                ForEach(Array(entry.briefItems.prefix(6).enumerated()), id: \.offset) { _, item in
                    HStack(alignment: .top, spacing: 8) {
                        Image(systemName: item["priority"] == "high"
                              ? "exclamationmark.circle.fill" : "circle.fill")
                            .foregroundStyle(item["priority"] == "high" ? .orange : .cyan)
                            .font(.caption2)
                            .padding(.top, 1)
                        Text(item["text"] ?? "")
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.9))
                            .lineLimit(2)
                    }
                }
            }

            Spacer()

            // Footer
            HStack {
                if !entry.agentAction.isEmpty {
                    Label(entry.agentAction, systemImage: "gearshape.fill")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
                Spacer()
                if entry.needsCount > 0 {
                    Label("\(entry.needsCount) need\(entry.needsCount == 1 ? "s" : "") you",
                          systemImage: "exclamationmark.circle.fill")
                        .font(.caption2.bold())
                        .foregroundStyle(.orange)
                }
            }
        }
        .padding(14)
    }
}

// MARK: - Accessory (Lock Screen) widget

struct JarvisAccessoryWidget: Widget {
    let kind = "JarvisAccessoryWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: JarvisTimelineProvider()) { entry in
            AccessoryWidgetView(entry: entry)
                .containerBackground(.black, for: .widget)
        }
        .configurationDisplayName("JARVIS")
        .description("JARVIS on your Lock Screen.")
        .supportedFamilies([.accessoryCircular, .accessoryRectangular, .accessoryInline])
    }
}

private struct AccessoryWidgetView: View {
    @Environment(\.widgetFamily) var family
    let entry: JarvisEntry

    var body: some View {
        switch family {
        case .accessoryCircular:
            ZStack {
                if entry.needsCount > 0 {
                    Circle().fill(.orange.opacity(0.2))
                    Text("\(entry.needsCount)")
                        .font(.title3.bold())
                        .foregroundStyle(.orange)
                } else {
                    Circle().fill(.cyan.opacity(0.15))
                    Image(systemName: modeIcon(entry.mode))
                        .foregroundStyle(.cyan)
                }
            }
        case .accessoryRectangular:
            VStack(alignment: .leading, spacing: 2) {
                Label("JARVIS", systemImage: modeIcon(entry.mode))
                    .font(.caption2.bold())
                    .foregroundStyle(.cyan)
                Text(entry.briefItems.first?["text"] ?? entry.agentAction)
                    .font(.caption2)
                    .lineLimit(2)
            }
        case .accessoryInline:
            Label(entry.needsCount > 0
                  ? "\(entry.needsCount) needs you"
                  : entry.weatherTemp + " · " + modeLabel(entry.mode),
                  systemImage: entry.needsCount > 0 ? "exclamationmark.circle" : modeIcon(entry.mode))
                .font(.caption2)
        default:
            EmptyView()
        }
    }
}

// MARK: - Shared helpers

func modeIcon(_ mode: String) -> String {
    switch mode {
    case "morning_brief": return "sun.horizon.fill"
    case "lunch_brief":   return "sun.max.fill"
    case "daily_recap":   return "moon.stars.fill"
    default:              return "j.circle.fill"
    }
}

func modeLabel(_ mode: String) -> String {
    switch mode {
    case "morning_brief": return "Morning Brief"
    case "lunch_brief":   return "Lunch Brief"
    case "daily_recap":   return "Daily Recap"
    default:              return "JARVIS"
    }
}
