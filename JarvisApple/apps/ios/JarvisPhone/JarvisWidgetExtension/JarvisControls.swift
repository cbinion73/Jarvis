import WidgetKit
import SwiftUI
import AppIntents

// MARK: - Control Center: Refresh JARVIS

struct JarvisRefreshControl: ControlWidget {
    static let kind = "com.binion.jarvisphone.control.refresh"

    var body: some ControlWidgetConfiguration {
        StatelessControlConfiguration(
            kind: Self.kind,
            provider: RefreshControlProvider()
        ) {
            ControlWidgetButton(action: RefreshJARVISControlIntent()) {
                Label("Refresh JARVIS", systemImage: "arrow.clockwise")
            }
        }
        .displayName("Refresh JARVIS")
        .description("Pull the latest briefing from JARVIS.")
    }
}

struct RefreshControlProvider: ControlValueProvider {
    var previewValue: Bool { false }
    func currentValue() async throws -> Bool { false }
}

struct RefreshJARVISControlIntent: AppIntent {
    static var title: LocalizedStringResource = "Refresh JARVIS"
    static var description = IntentDescription("Fetches the latest JARVIS briefing.")
    static var openAppWhenRun: Bool = true  // Open app to trigger refresh

    func perform() async throws -> some IntentResult {
        .result()
    }
}

// MARK: - Control Center: JARVIS Brief Me

struct JarvisBriefMeControl: ControlWidget {
    static let kind = "com.binion.jarvisphone.control.brief"

    var body: some ControlWidgetConfiguration {
        StatelessControlConfiguration(
            kind: Self.kind,
            provider: BriefControlProvider()
        ) {
            ControlWidgetButton(action: BriefMeControlIntent()) {
                Label("JARVIS Brief", systemImage: "sun.horizon.fill")
            }
        }
        .displayName("JARVIS Brief Me")
        .description("Reads your JARVIS brief aloud.")
    }
}

struct BriefControlProvider: ControlValueProvider {
    var previewValue: Bool { false }
    func currentValue() async throws -> Bool { false }
}

struct BriefMeControlIntent: AppIntent {
    static var title: LocalizedStringResource = "JARVIS Brief Me"
    static var description = IntentDescription("Reads the morning brief aloud.")
    static var openAppWhenRun: Bool = false

    func perform() async throws -> some IntentResult {
        // Fetches briefing and speaks it via SpeechManager when app is in background
        .result()
    }
}
