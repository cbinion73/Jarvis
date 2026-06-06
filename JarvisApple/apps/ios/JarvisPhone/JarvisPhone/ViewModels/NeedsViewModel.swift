import Foundation
import JarvisKit

@MainActor
final class NeedsViewModel: ObservableObject {

    @Published var items: [NeedsItem] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var lastApprovedId: String?
    @Published var lastActionId: String?
    @Published var lastActionMessage: String?

    private let client = AppleAPIClient.shared

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            items = try await client.fetchNeeds()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func approve(item: NeedsItem) async {
        do {
            let success = try await client.approve(requestId: item.id)
            if success {
                lastApprovedId = item.id
                lastActionId = item.id
                lastActionMessage = "Approved \(item.text)"
                await load()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func reject(item: NeedsItem, reason: String = "") async {
        do {
            let success = try await client.reject(requestId: item.id, reason: reason)
            if success {
                lastActionId = item.id
                lastActionMessage = "Rejected \(item.text)"
                await load()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func cancel(item: NeedsItem) async {
        do {
            let success = try await client.cancel(requestId: item.id)
            if success {
                lastActionId = item.id
                lastActionMessage = "Cancelled \(item.text)"
                await load()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func refresh() async {
        await load()
    }
}
