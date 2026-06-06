import Foundation
import JarvisKit

@MainActor
final class HealthViewModel: ObservableObject {

    @Published var summary: HealthSummary?
    @Published var checkins: [HealthCheckInEntry] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let client = AppleAPIClient.shared

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            async let summaryTask = client.fetchHealthSummary()
            async let checkinsTask = client.fetchHealthCheckins()
            summary = try await summaryTask
            checkins = try await checkinsTask.entries
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

    func submitCheckin(
        symptoms: String,
        note: String,
        energyLevel: Int,
        sleepHours: Double,
        stressLevel: Int
    ) async throws {
        _ = try await client.submitHealthCheckin(
            symptoms: symptoms,
            note: note,
            energyLevel: energyLevel,
            sleepHours: sleepHours,
            stressLevel: stressLevel
        )
        try? await Task.sleep(nanoseconds: 150_000_000)
        await load()
    }
}
