import Foundation
import JarvisKit

@MainActor
final class BriefingViewModel: ObservableObject {

    @Published var packet: BriefingPacket?
    @Published var appState: AppStateOverview?
    @Published var focusState: FocusStateOverview?
    @Published var controlPlaneState: ControlPlaneOverview?
    @Published var catalystOverview: CatalystOverview?
    @Published var chronicleOverview: ChronicleOverview?
    @Published var publishingOverview: PublishOverview?
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var latestOpenLoopAction: BriefingOpenLoopActionResult?

    private let client = AppleAPIClient.shared
    private let speechManager = SpeechManager.shared

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            async let briefing = client.fetchBriefing()
            async let state = client.fetchAppState()
            packet = try await briefing
            appState = try await state
            async let focus = try? client.fetchFocusState()
            async let control = try? client.fetchControlPlaneState()
            async let catalyst = try? client.fetchCatalyst()
            async let chronicle = try? client.fetchChronicle()
            async let publishing = try? client.fetchPublishing()
            focusState = await focus
            controlPlaneState = await control
            catalystOverview = await catalyst
            chronicleOverview = await chronicle
            publishingOverview = await publishing
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
            async let focus = try? client.fetchFocusState()
            async let control = try? client.fetchControlPlaneState()
            async let catalyst = try? client.fetchCatalyst()
            async let chronicle = try? client.fetchChronicle()
            async let publishing = try? client.fetchPublishing()
            focusState = await focus
            controlPlaneState = await control
            catalystOverview = await catalyst
            chronicleOverview = await chronicle
            publishingOverview = await publishing
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

    @discardableResult
    func stageStewardshipLaneReview(_ laneId: String, note: String = "") async -> StewardshipLaneActionResult? {
        do {
            let result = try await client.stageStewardshipLaneReview(laneId, note: note)
            await load()
            return result
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    /// Send a voice command transcript to the JARVIS /speak endpoint.
    func sendVoiceCommand(_ text: String) async {
        guard !text.isEmpty else { return }
        do {
            let result = try await client.speak(text: text)
            if result.speak {
                speechManager.speak(result.spokenText)
            }
            await load()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @discardableResult
    func applyOpenLoopAction(_ item: BriefingOpenLoopItem, action: String, note: String = "") async -> BriefingOpenLoopActionResult? {
        do {
            let result = try await client.applyBriefingOpenLoopAction(
                itemId: item.itemId,
                domain: item.domain,
                action: action,
                title: item.title,
                summary: item.summary,
                note: note
            )
            await load()
            latestOpenLoopAction = result
            return result
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }
}
