import WidgetKit
import SwiftUI
import AppIntents

// MARK: - Control Center: Refresh JARVIS

struct RefreshJARVISControlIntent: AppIntent {
    static let title: LocalizedStringResource = "Refresh JARVIS"
    static let description = IntentDescription("Fetches the latest JARVIS briefing.")
    static let openAppWhenRun: Bool = true

    func perform() async throws -> some IntentResult {
        .result()
    }
}

// MARK: - Control Center: JARVIS Brief Me

struct BriefMeControlIntent: AppIntent {
    static let title: LocalizedStringResource = "JARVIS Brief Me"
    static let description = IntentDescription("Reads the morning brief aloud.")
    static let openAppWhenRun: Bool = false

    func perform() async throws -> some IntentResult {
        .result()
    }
}
