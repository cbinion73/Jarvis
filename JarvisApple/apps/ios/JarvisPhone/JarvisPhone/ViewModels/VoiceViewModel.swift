import Foundation
import JarvisKit

@MainActor
final class VoiceViewModel: ObservableObject {

    static let shared = VoiceViewModel()

    struct Exchange: Identifiable {
        let id        = UUID()
        let userText:  String
        let response:  String
        let agent:     String
        let timestamp  = Date()
    }

    @Published var exchanges:     [Exchange] = []
    @Published var isThinking     = false
    @Published var errorMessage:  String?
    @Published var isConversationActive = false
    @Published var conversationStatus = "Idle"
    @Published var voiceState: VoiceConsoleState?
    @Published var isDuplexArmed = false

    private let client = AppleAPIClient.shared
    private let speechManager = SpeechManager.shared
    private let speechRecognition = SpeechRecognitionManager.shared
    private var silenceTask: Task<Void, Never>?
    private var conversationId = ""

    private init() {}

    func send(_ text: String) async {
        await performSend(text, continueConversation: false)
    }

    func refreshVoiceState() async {
        do {
            let state = try await client.fetchVoiceState(conversationId: conversationId)
            voiceState = state
            if conversationId.isEmpty {
                conversationId = state.conversation.conversationId
            }
        } catch {
            // Voice UI should remain usable even if the console snapshot is unavailable.
        }
    }

    func activateConversation(launch: VoiceConversationLaunchRequest) {
        isConversationActive = true
        errorMessage = nil
        conversationStatus = launch.utterance.isEmpty
            ? "Listening for your first request"
            : "Starting from Siri"
        speechManager.stopSpeaking()
        speechRecognition.stopListening()
        isDuplexArmed = false

        if launch.utterance.isEmpty {
            Task { @MainActor [weak self] in
                await self?.refreshVoiceState()
                try? await Task.sleep(for: .seconds(0.8))
                guard let self, self.isConversationActive else { return }
                self.startListeningTurn()
            }
        } else {
            Task { await performSend(launch.utterance, continueConversation: true) }
        }
    }

    func endConversation(reason: String = "Conversation ended") {
        silenceTask?.cancel()
        silenceTask = nil
        if speechRecognition.isListening {
            speechRecognition.stopListening()
        }
        isDuplexArmed = false
        isConversationActive = false
        conversationStatus = reason
    }

    func toggleConversationMicrophone() {
        if speechRecognition.isListening {
            speechRecognition.stopListening()
        } else if isConversationActive {
            startListeningTurn()
        } else {
            activateConversation(launch: VoiceConversationLaunchRequest(source: "in_app"))
        }
    }

    func ensureConversationIsLive() {
        if voiceState == nil {
            Task { await refreshVoiceState() }
        }
        guard isConversationActive else { return }
        guard speechRecognition.isListening == false else { return }
        guard isThinking == false else { return }
        startListeningTurn()
    }

    private func startListeningTurn() {
        guard speechRecognition.isListening == false else {
            conversationStatus = isDuplexArmed ? "Listening while JARVIS speaks" : "Listening"
            return
        }
        guard isThinking == false else { return }
        silenceTask?.cancel()
        isConversationActive = true
        conversationStatus = isDuplexArmed ? "Listening while JARVIS speaks" : "Listening"
        speechRecognition.startListening(onPartial: { [weak self] partial in
            Task { @MainActor [weak self] in
                self?.handlePartialTranscript(partial)
            }
        }) { [weak self] text in
            Task { @MainActor [weak self] in
                self?.handleRecognizedTurn(text)
            }
        }
        silenceTask = Task { [weak self] in
            try? await Task.sleep(for: .seconds(8))
            await MainActor.run {
                guard let self else { return }
                guard self.speechRecognition.isListening else { return }
                let transcript = self.speechRecognition.transcript.trimmingCharacters(in: .whitespacesAndNewlines)
                guard transcript.isEmpty else { return }
                self.endConversation(reason: "Idle")
            }
        }
    }

    private func handleRecognizedTurn(_ text: String) {
        silenceTask?.cancel()
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            isDuplexArmed = false
            endConversation(reason: "Idle")
            return
        }
        if Self.isClosePhrase(trimmed) {
            isDuplexArmed = false
            endConversation(reason: "Idle")
            return
        }
        if speechManager.isSpeaking {
            speechManager.stopSpeaking()
        }
        isDuplexArmed = false
        Task { await performSend(trimmed, continueConversation: isConversationActive) }
    }

    private func handlePartialTranscript(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        guard isConversationActive else { return }
        guard speechManager.isSpeaking else { return }
        if isDuplexArmed {
            conversationStatus = "Interrupted — JARVIS is listening"
        }
        speechManager.stopSpeaking()
    }

    private func performSend(_ text: String, continueConversation: Bool) async {
        guard !text.trimmingCharacters(in: .whitespaces).isEmpty else { return }
        isThinking    = true
        errorMessage  = nil
        isDuplexArmed = false
        conversationStatus = "JARVIS is thinking"
        do {
            let result = try await client.speak(text: text, conversationId: conversationId.isEmpty ? nil : conversationId)
            if !result.conversationId.isEmpty {
                conversationId = result.conversationId
            }
            exchanges.append(Exchange(
                userText: text,
                response: result.displayText,
                agent:    result.agent
            ))
            await refreshVoiceState()
            if result.speak {
                if continueConversation {
                    armDuplexFollowUpWindow()
                }
                speechManager.speak(
                    result.spokenText,
                    preferDuplex: continueConversation
                ) { [weak self] in
                    Task { @MainActor [weak self] in
                        self?.resumeConversationIfNeeded(continueConversation)
                    }
                }
            } else {
                resumeConversationIfNeeded(continueConversation)
            }
        } catch {
            errorMessage = error.localizedDescription
            conversationStatus = "Error"
            isConversationActive = false
            isDuplexArmed = false
        }
        isThinking = false
    }

    private func armDuplexFollowUpWindow() {
        guard isConversationActive else { return }
        guard !speechRecognition.isListening else {
            isDuplexArmed = true
            conversationStatus = "JARVIS is speaking. Interrupt anytime."
            return
        }
        isDuplexArmed = true
        startListeningTurn()
        conversationStatus = "JARVIS is speaking. Interrupt anytime."
    }

    private func resumeConversationIfNeeded(_ continueConversation: Bool) {
        guard continueConversation else {
            conversationStatus = "Idle"
            isDuplexArmed = false
            return
        }
        if speechRecognition.isListening {
            conversationStatus = "Listening"
            isDuplexArmed = false
            return
        }
        isDuplexArmed = false
        startListeningTurn()
    }

    private static func isClosePhrase(_ text: String) -> Bool {
        let normalized = text.lowercased()
        return normalized.contains("thanks jarvis")
            || normalized.contains("thank you jarvis")
            || normalized.contains("bye jarvis")
            || normalized.contains("goodbye jarvis")
            || normalized == "thanks"
            || normalized == "thank you"
    }

    func clear() { exchanges.removeAll() }
}
