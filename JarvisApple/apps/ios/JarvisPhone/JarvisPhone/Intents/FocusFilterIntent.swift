import AppIntents
import JarvisKit

/// JARVIS Focus Filter — iOS reads this when the user configures a Focus mode.
struct JarvisFocusFilter: SetFocusFilterIntent {

    static let title: LocalizedStringResource = "Adjust JARVIS"
    static let description = IntentDescription(
        "Tell JARVIS how to behave during this Focus mode.",
        categoryName: "JARVIS"
    )

    static let typeDisplayRepresentation: TypeDisplayRepresentation = "JARVIS Focus Filter"

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: "JARVIS: \(jarvisMode?.rawValue ?? "default")")
    }

    // MARK: - Parameters

    @Parameter(title: "Mode", description: "Which JARVIS mode to activate")
    var jarvisMode: JarvisFocusMode?

    @Parameter(title: "Hold non-urgent approvals",
               description: "Don't send approval push notifications unless risk is high")
    var holdApprovals: Bool?

    @Parameter(title: "Silence briefing updates",
               description: "Suppress proactive briefing notifications")
    var silenceBriefings: Bool?

    // MARK: - Perform

    func perform() async throws -> some IntentResult {
        let payload: [String: Any] = [
            "focus_active":      true,
            "jarvis_mode":       jarvisMode?.rawValue ?? "morning_brief",
            "hold_approvals":    holdApprovals ?? false,
            "silence_briefings": silenceBriefings ?? false,
            "source":            "focus_filter",
        ]
        await sendFocusState(payload)
        return .result()
    }

    private func sendFocusState(_ payload: [String: Any]) async {
        guard let url  = URL(string: JARVISEnvironment.baseURL.absoluteString + "/api/apple/focus"),
              let body = try? JSONSerialization.data(withJSONObject: payload) else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body
        _ = try? await URLSession.shared.data(for: req)
    }
}

// MARK: - Focus mode enum

enum JarvisFocusMode: String, AppEnum {
    case morning   = "morning_brief"
    case work      = "work"
    case lunch     = "lunch_brief"
    case evening   = "daily_recap"
    case sleep     = "sleep"
    case personal  = "personal"

    static let typeDisplayRepresentation: TypeDisplayRepresentation = "JARVIS Mode"
    static let caseDisplayRepresentations: [JarvisFocusMode: DisplayRepresentation] = [
        .morning:  "Morning Brief",
        .work:     "Work Focus",
        .lunch:    "Lunch Brief",
        .evening:  "Daily Recap",
        .sleep:    "Sleep (quiet)",
        .personal: "Personal Time",
    ]
}

// MARK: - Focus ended intent

struct JarvisFocusEndedIntent: AppIntent {
    static let title: LocalizedStringResource = "JARVIS Focus Ended"

    func perform() async throws -> some IntentResult {
        let payload: [String: Any] = ["focus_active": false, "source": "focus_filter"]
        guard let url  = URL(string: JARVISEnvironment.baseURL.absoluteString + "/api/apple/focus"),
              let body = try? JSONSerialization.data(withJSONObject: payload) else {
            return .result()
        }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body
        _ = try? await URLSession.shared.data(for: req)
        return .result()
    }
}
