import WidgetKit
import SwiftUI

@main
struct JarvisComplicationBundle: WidgetBundle {
    var body: some Widget {
        JarvisComplication()
    }
}

struct JarvisComplication: Widget {
    let kind = "com.binion.jarvisphone.complication"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: JarvisComplicationProvider()) { entry in
            JarvisComplicationEntryView(entry: entry)
                .containerBackground(.black, for: .widget)
        }
        .configurationDisplayName("JARVIS")
        .description("Briefing mode and pending approvals.")
        .supportedFamilies([
            .accessoryCircular,
            .accessoryRectangular,
            .accessoryInline,
            .accessoryCorner,
        ])
    }
}

// MARK: - Entry view router

struct JarvisComplicationEntryView: View {
    let entry: JarvisEntry
    @Environment(\.widgetFamily) var family

    var body: some View {
        switch family {
        case .accessoryCircular:    CircularComplicationView(entry: entry)
        case .accessoryRectangular: RectangularComplicationView(entry: entry)
        case .accessoryInline:      InlineComplicationView(entry: entry)
        case .accessoryCorner:      CornerComplicationView(entry: entry)
        default:                    CircularComplicationView(entry: entry)
        }
    }
}
