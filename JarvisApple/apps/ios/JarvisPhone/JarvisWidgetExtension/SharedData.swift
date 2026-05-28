import Foundation

/// Keys for App Group shared UserDefaults.
/// Both JarvisPhone (writer) and JarvisWidgetExtension (reader) use these.
enum SharedDataKey {
    static let greeting      = "jarvis.shared.greeting"
    static let mode          = "jarvis.shared.mode"
    static let needsCount    = "jarvis.shared.needs_count"
    static let briefItems    = "jarvis.shared.brief_items"    // [[String:String]]
    static let weatherTemp   = "jarvis.shared.wx_temp"
    static let weatherCond   = "jarvis.shared.wx_cond"
    static let weatherKey    = "jarvis.shared.wx_visual_key"
    static let agentName     = "jarvis.shared.agent_name"
    static let agentAction   = "jarvis.shared.agent_action"
    static let lastUpdated   = "jarvis.shared.last_updated"
}

let appGroupID = "group.com.binion.jarvisphone"

extension UserDefaults {
    static var jarvis: UserDefaults {
        UserDefaults(suiteName: appGroupID) ?? .standard
    }
}

/// Snapshot of JARVIS data as read from App Group store.
struct JarvisSnapshot {
    let greeting:    String
    let mode:        String
    let needsCount:  Int
    let briefItems:  [[String: String]]
    let weatherTemp: String
    let weatherCond: String
    let weatherKey:  String
    let agentName:   String
    let agentAction: String
    let lastUpdated: Date?

    static func load() -> JarvisSnapshot {
        let ud = UserDefaults.jarvis
        return JarvisSnapshot(
            greeting:    ud.string(forKey: SharedDataKey.greeting)     ?? "Good morning, Sir.",
            mode:        ud.string(forKey: SharedDataKey.mode)         ?? "morning_brief",
            needsCount:  ud.integer(forKey: SharedDataKey.needsCount),
            briefItems:  (ud.array(forKey: SharedDataKey.briefItems)   as? [[String: String]]) ?? [],
            weatherTemp: ud.string(forKey: SharedDataKey.weatherTemp)  ?? "--°",
            weatherCond: ud.string(forKey: SharedDataKey.weatherCond)  ?? "",
            weatherKey:  ud.string(forKey: SharedDataKey.weatherKey)   ?? "clear_day",
            agentName:   ud.string(forKey: SharedDataKey.agentName)    ?? "",
            agentAction: ud.string(forKey: SharedDataKey.agentAction)  ?? "Standing by",
            lastUpdated: ud.object(forKey: SharedDataKey.lastUpdated)  as? Date
        )
    }
}
