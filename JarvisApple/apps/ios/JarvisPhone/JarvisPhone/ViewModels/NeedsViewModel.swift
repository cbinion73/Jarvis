import Foundation
import JarvisKit

@MainActor
final class NeedsViewModel: ObservableObject {

    @Published var items: [NeedsItem] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var lastApprovedId: String?

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
                items.removeAll { $0.id == item.id }
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func refresh() async {
        await load()
    }
}
