import Foundation
import JarvisKit

@MainActor
final class VoiceViewModel: ObservableObject {

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

    private let client = AppleAPIClient.shared

    func send(_ text: String) async {
        guard !text.trimmingCharacters(in: .whitespaces).isEmpty else { return }
        isThinking    = true
        errorMessage  = nil
        do {
            let result = try await client.speak(text: text)
            exchanges.append(Exchange(
                userText: text,
                response: result.response,
                agent:    result.agent
            ))
        } catch {
            errorMessage = error.localizedDescription
        }
        isThinking = false
    }

    func clear() { exchanges.removeAll() }
}
