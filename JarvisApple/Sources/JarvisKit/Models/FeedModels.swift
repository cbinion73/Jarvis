import Foundation

public struct HealthDailyFeedSummary: Codable, Equatable, Sendable {
    public let status: String
    public let headline: String
    public let signals: [String]
    public let recommendations: [String]
    public let escalations: [String]

    public init(
        status: String,
        headline: String,
        signals: [String],
        recommendations: [String],
        escalations: [String]
    ) {
        self.status = status
        self.headline = headline
        self.signals = signals
        self.recommendations = recommendations
        self.escalations = escalations
    }
}
