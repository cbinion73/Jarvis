import Foundation
import JarvisKit

@MainActor
final class HealthViewModel: ObservableObject {

    @Published var summary: HealthSummary?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let client = AppleAPIClient.shared

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            summary = try await client.fetchHealthSummary()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func refresh() async {
        await load()
    }

    // MARK: - Readiness colour

    var readinessColor: String {
        switch summary?.readiness {
        case "good":     return "green"
        case "moderate": return "yellow"
        default:         return "red"
        }
    }
}
