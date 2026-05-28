#if canImport(ActivityKit) && !os(macOS)
import ActivityKit

/// Shared Live Activity attributes — used by both JarvisPhone (to start/update)
/// and JarvisWidgetExtension (to render the Dynamic Island + Lock Screen).
public struct JarvisActivityAttributes: ActivityAttributes {

    // MARK: - Dynamic content (updated in real-time)

    public struct ContentState: Codable, Hashable, Sendable {
        /// Current agent name, e.g. "FRIDAY"
        public var agentName: String
        /// What the agent is doing, e.g. "Processing 3 emails…"
        public var action: String
        /// How many items need user attention
        public var needsCount: Int
        /// Current mode: "morning_brief" | "lunch_brief" | "daily_recap"
        public var mode: String
        /// Brief one-liner for Lock Screen
        public var statusLine: String

        public init(
            agentName: String  = "",
            action: String     = "Standing by",
            needsCount: Int    = 0,
            mode: String       = "morning_brief",
            statusLine: String = "JARVIS is ready"
        ) {
            self.agentName  = agentName
            self.action     = action
            self.needsCount = needsCount
            self.mode       = mode
            self.statusLine = statusLine
        }
    }

    // MARK: - Static content (set at start, never changes)

    public var actorName: String   // "Chris"

    public init(actorName: String = "Sir") {
        self.actorName = actorName
    }
}
#endif
