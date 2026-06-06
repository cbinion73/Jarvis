import AppIntents
import Foundation

@available(iOS 18.0, *)
struct AskJarvisIntent: AppIntent {

    @Parameter(
        title: "Request",
        requestValueDialog: IntentDialog("What would you like to ask JARVIS?"),
        inputConnectionBehavior: .connectToPreviousIntentResult
    )
    var request: String

    nonisolated(unsafe) static var title: LocalizedStringResource = "Ask JARVIS"
    nonisolated(unsafe) static var description = IntentDescription(
        "Wake JARVIS and continue the conversation in the app.",
        categoryName: "JARVIS"
    )
    nonisolated(unsafe) static var openAppWhenRun = true

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let resolvedRequest = try await resolvedUtterance()
        await MainActor.run {
            VoiceConversationLaunchCenter.shared.queueLaunch(
                VoiceConversationLaunchRequest(utterance: resolvedRequest, source: "siri.ask")
            )
        }
        return .result(dialog: "Opening JARVIS.")
    }

    private func resolvedUtterance() async throws -> String {
        let trimmed = request.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty == false {
            return trimmed
        }
        let prompted = try await $request.requestValue(
            IntentDialog("What would you like to ask JARVIS?")
        )
        return prompted.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

@available(iOS 18.0, *)
struct StartJarvisConversationIntent: AppIntent {

    nonisolated(unsafe) static var title: LocalizedStringResource = "Talk to JARVIS"
    nonisolated(unsafe) static var description = IntentDescription(
        "Open JARVIS directly into conversation mode.",
        categoryName: "JARVIS"
    )
    nonisolated(unsafe) static var openAppWhenRun = true

    func perform() async throws -> some IntentResult & ProvidesDialog {
        await MainActor.run {
            VoiceConversationLaunchCenter.shared.queueLaunch(
                VoiceConversationLaunchRequest(source: "siri.start")
            )
        }
        return .result(dialog: "Opening JARVIS.")
    }
}
