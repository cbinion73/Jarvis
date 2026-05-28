import Foundation
import JarvisKit

@MainActor
final class BriefingViewModel: ObservableObject {

    @Published var packet: BriefingPacket?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let client = AppleAPIClient.shared

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            packet = try await client.fetchBriefing()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func refresh() async {
        await load()
    }

    /// Send a voice command transcript to the JARVIS /speak endpoint.
    func sendVoiceCommand(_ text: String) async {
        guard !text.isEmpty,
              let url  = URL(string: JARVISEnvironment.baseURL.absoluteString + "/api/apple/speak"),
              let body = try? JSONSerialization.data(withJSONObject: ["text": text, "actor": "chris"])
        else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body
        _ = try? await URLSession.shared.data(for: req)
        // Refresh brief after command
        await load()
    }
}
