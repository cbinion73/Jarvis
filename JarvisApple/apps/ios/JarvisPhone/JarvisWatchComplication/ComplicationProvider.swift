import WidgetKit
import SwiftUI

// MARK: - Timeline entry

struct JarvisEntry: TimelineEntry {
    let date: Date
    let needsCount: Int
    let mode: String
    let greeting: String
}

// MARK: - Timeline provider

struct JarvisComplicationProvider: TimelineProvider {

    func placeholder(in context: Context) -> JarvisEntry {
        JarvisEntry(date: .now, needsCount: 0, mode: "morning", greeting: "Good morning")
    }

    func getSnapshot(in context: Context, completion: @escaping (JarvisEntry) -> Void) {
        completion(loadEntry())
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<JarvisEntry>) -> Void) {
        let entry = loadEntry()
        // Refresh every 15 minutes
        let next = Calendar.current.date(byAdding: .minute, value: 15, to: .now)!
        completion(Timeline(entries: [entry], policy: .after(next)))
    }

    // MARK: - Read from UserDefaults (written by WatchViewModel)

    private func loadEntry() -> JarvisEntry {
        let ud = UserDefaults.standard
        return JarvisEntry(
            date:       .now,
            needsCount: ud.integer(forKey: "jarvis.watch.needs_count"),
            mode:       ud.string(forKey: "jarvis.watch.mode")     ?? "morning",
            greeting:   ud.string(forKey: "jarvis.watch.greeting") ?? "JARVIS"
        )
    }
}
