import Foundation

let appGroupID = "group.com.binion.jarvisphone"

enum SharedDataKey {
    static let greeting      = "jarvis.shared.greeting"
    static let mode          = "jarvis.shared.mode"
    static let needsCount    = "jarvis.shared.needs_count"
    static let briefItems    = "jarvis.shared.brief_items"
    static let weatherTemp   = "jarvis.shared.wx_temp"
    static let weatherCond   = "jarvis.shared.wx_cond"
    static let weatherKey    = "jarvis.shared.wx_visual_key"
    static let agentName     = "jarvis.shared.agent_name"
    static let agentAction   = "jarvis.shared.agent_action"
    static let lastUpdated   = "jarvis.shared.last_updated"
}

extension UserDefaults {
    static var jarvis: UserDefaults {
        UserDefaults(suiteName: appGroupID) ?? .standard
    }
}
