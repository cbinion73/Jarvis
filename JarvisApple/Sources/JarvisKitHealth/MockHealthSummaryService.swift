import Foundation
import JarvisKit

public protocol HealthSummaryProviding: Sendable {
    func currentSummary() async -> HealthDailyFeedSummary
}

public struct MockHealthSummaryService: HealthSummaryProviding {
    public init() {}

    public func currentSummary() async -> HealthDailyFeedSummary {
        HealthDailyFeedSummary(
            status: "monitor",
            headline: "Recovery looks low today.",
            signals: [
                "Sleep down 3 nights",
                "Resting heart rate elevated",
                "No recovery day logged"
            ],
            recommendations: [
                "Hydrate early",
                "Keep activity light today",
                "Aim for earlier sleep tonight"
            ],
            escalations: []
        )
    }
}
