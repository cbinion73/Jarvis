import ActivityKit
import JarvisKit

/// Starts, updates, and ends the JARVIS Live Activity (Dynamic Island + Lock Screen).
@MainActor
final class LiveActivityManager: ObservableObject {

    static let shared = LiveActivityManager()

    @Published var isActive = false

    private var activity: Activity<JarvisActivityAttributes>?

    private override init() {
        // Adopt any already-running activity on cold start
        activity = Activity<JarvisActivityAttributes>.activities.first
        isActive = activity != nil
    }

    // MARK: - Start

    func start(actor: String = "Sir") {
        guard ActivityAuthorizationInfo().areActivitiesEnabled else { return }
        guard activity == nil else { return }

        let attrs   = JarvisActivityAttributes(actorName: actor)
        let state   = JarvisActivityAttributes.ContentState()
        let content = ActivityContent(state: state, staleDate: .now + 3600)

        do {
            activity = try Activity.request(
                attributes: attrs,
                content: content,
                pushType: nil
            )
            isActive = true
        } catch {
            print("[LiveActivity] start error: \(error)")
        }
    }

    // MARK: - Update

    func update(agentName: String = "", action: String, needsCount: Int = 0,
                mode: String = "morning_brief", statusLine: String = "") {
        guard let activity else { return }
        let state = JarvisActivityAttributes.ContentState(
            agentName:  agentName,
            action:     action,
            needsCount: needsCount,
            mode:       mode,
            statusLine: statusLine.isEmpty ? action : statusLine
        )
        Task {
            await activity.update(ActivityContent(state: state, staleDate: .now + 3600))
        }
    }

    /// Convenience: update from a BriefingPacket
    func updateFromBriefing(mode: String, needsCount: Int) {
        update(
            action:     needsCount > 0 ? "\(needsCount) item\(needsCount == 1 ? "" : "s") need your attention" : "Briefing ready",
            needsCount: needsCount,
            mode:       mode
        )
    }

    // MARK: - End

    func end() {
        Task {
            let state = JarvisActivityAttributes.ContentState(action: "Session ended")
            await activity?.end(
                ActivityContent(state: state, staleDate: .now),
                dismissalPolicy: .after(.now + 5)
            )
            activity = nil
            isActive = false
        }
    }
}
