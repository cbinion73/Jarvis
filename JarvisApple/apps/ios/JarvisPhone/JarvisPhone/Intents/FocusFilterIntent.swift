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
        let payload = FocusPayload(
            focusActive: true,
            jarvisMode: jarvisMode?.rawValue ?? "morning_brief",
            holdApprovals: holdApprovals ?? false,
            silenceBriefings: silenceBriefings ?? false,
            source: "focus_filter"
        )
        await sendFocusState(payload)
        return .result()
    }

    private func sendFocusState(_ payload: FocusPayload) async {
        try? await AppleAPIClient.shared.postAcknowledged("/api/apple/focus", body: payload)
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
        let payload = FocusPayload(
            focusActive: false,
            jarvisMode: nil,
            holdApprovals: nil,
            silenceBriefings: nil,
            source: "focus_filter"
        )
        try? await AppleAPIClient.shared.postAcknowledged("/api/apple/focus", body: payload)
        return .result()
    }
}

private struct FocusPayload: Encodable, Sendable {
    let focusActive: Bool
    let jarvisMode: String?
    let holdApprovals: Bool?
    let silenceBriefings: Bool?
    let source: String

    enum CodingKeys: String, CodingKey {
        case source
        case focusActive = "focus_active"
        case jarvisMode = "jarvis_mode"
        case holdApprovals = "hold_approvals"
        case silenceBriefings = "silence_briefings"
    }
}
