import Foundation

public struct FocusStateOverview: Codable, Sendable {
    public let focusActive: Bool
    public let updatedAt: String
    public let source: String
    public let sourceFresh: Bool
    public let interruptionPosture: FocusInterruptionPosture
    public let suppressionRules: [FocusSuppressionRule]
    public let summary: FocusStateSummary

    enum CodingKeys: String, CodingKey {
        case source, summary
        case focusActive = "focus_active"
        case updatedAt = "updated_at"
        case sourceFresh = "source_fresh"
        case interruptionPosture = "interruption_posture"
        case suppressionRules = "suppression_rules"
    }
}

public struct FocusInterruptionPosture: Codable, Sendable {
    public let mode: String
    public let label: String
    public let reason: String
    public let recommendedDelivery: String
    public let focusActive: Bool
    public let quietHours: Bool
    public let hourLocal: Int
    public let needsCount: Int
    public let alertCount: Int
    public let presentMembers: [String]
    public let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case mode, label, reason
        case recommendedDelivery = "recommended_delivery"
        case focusActive = "focus_active"
        case quietHours = "quiet_hours"
        case hourLocal = "hour_local"
        case needsCount = "needs_count"
        case alertCount = "alert_count"
        case presentMembers = "present_members"
        case updatedAt = "updated_at"
    }
}

public struct FocusSuppressionRule: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let detail: String
    public let active: Bool
}

public struct FocusStateSummary: Codable, Sendable {
    public let label: String
    public let detail: String
    public let recommendedDelivery: String

    enum CodingKeys: String, CodingKey {
        case label, detail
        case recommendedDelivery = "recommended_delivery"
    }
}
