import Foundation
import JarvisKit

@MainActor
final class BriefingViewModel: ObservableObject {

    @Published var packet: BriefingPacket?
    @Published var appState: AppStateOverview?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let client = AppleAPIClient.shared

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            async let briefing = client.fetchBriefing()
            async let state = client.fetchAppState()
            packet = try await briefing
            appState = try await state
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func refresh() async {
        await load()
    }

    func refreshAppState() async {
        do {
            appState = try await client.fetchAppState()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @discardableResult
    func approve(requestId: String) async -> Bool {
        do {
            let success = try await client.approve(requestId: requestId)
            if success {
                await load()
            }
            return success
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    /// Send a voice command transcript to the JARVIS /speak endpoint.
    func sendVoiceCommand(_ text: String) async {
        guard !text.isEmpty else { return }
        _ = try? await client.speak(text: text)
        // Refresh brief after command
        await load()
    }
}
