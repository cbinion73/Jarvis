import Foundation
import WidgetKit
import JarvisKit

/// Writes the latest JARVIS snapshot to the App Group UserDefaults
/// so widgets and complications can read it without network calls.
enum SharedDataWriter {

    static func write(
        greeting: String,
        mode: String,
        needsCount: Int,
        briefItems: [[String: String]],
        weatherTemp: String  = "",
        weatherCond: String  = "",
        weatherKey: String   = "clear_day",
        agentName: String    = "",
        agentAction: String  = ""
    ) {
        let ud = UserDefaults.jarvis
        ud.set(greeting,    forKey: SharedDataKey.greeting)
        ud.set(mode,        forKey: SharedDataKey.mode)
        ud.set(needsCount,  forKey: SharedDataKey.needsCount)
        ud.set(briefItems,  forKey: SharedDataKey.briefItems)
        ud.set(weatherTemp, forKey: SharedDataKey.weatherTemp)
        ud.set(weatherCond, forKey: SharedDataKey.weatherCond)
        ud.set(weatherKey,  forKey: SharedDataKey.weatherKey)
        ud.set(agentName,   forKey: SharedDataKey.agentName)
        ud.set(agentAction, forKey: SharedDataKey.agentAction)
        ud.set(Date(),      forKey: SharedDataKey.lastUpdated)
        // Also store base URL so Notification Content Extension can use it
        ud.set(JARVISEnvironment.baseURL.absoluteString, forKey: "jarvis.base_url")

        // Reload all widget timelines immediately
        WidgetCenter.shared.reloadAllTimelines()
    }
}
