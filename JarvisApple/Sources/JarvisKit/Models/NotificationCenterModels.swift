import Foundation

public struct NotificationCenterOverview: Codable, Sendable {
    public let notifications: [NotificationCenterItem]
}

public struct NotificationCenterItem: Codable, Identifiable, Sendable {
    public let id: String
    public let eventId: String
    public let category: String
    public let title: String
    public let detail: String
    public let body: String
    public let severity: String
    public let status: String
    public let createdAt: String
    public let updatedAt: String
    public let expiresAt: String
    public let audience: String
    public let deliveryMode: String
    public let navigationTarget: String
    public let availableActions: [String]
    public let whyNow: String
    public let decisionReason: String?
    public let sourceSummary: String
    public let postureSnapshot: NotificationPostureSnapshot?
    public let badge: Int

    enum CodingKeys: String, CodingKey {
        case id, category, title, detail, body, severity, status, audience, badge
        case eventId = "event_id"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case expiresAt = "expires_at"
        case deliveryMode = "delivery_mode"
        case navigationTarget = "navigation_target"
        case availableActions = "available_actions"
        case whyNow = "why_now"
        case decisionReason = "decision_reason"
        case sourceSummary = "source_summary"
        case postureSnapshot = "posture_snapshot"
    }
}

public struct NotificationPostureSnapshot: Codable, Sendable {
    public let mode: String?
    public let label: String?
    public let reason: String?
    public let recommendedDelivery: String?
    public let quietHours: Bool?
    public let hourLocal: Int?
    public let needsCount: Int?
    public let alertCount: Int?

    enum CodingKeys: String, CodingKey {
        case mode, label, reason
        case recommendedDelivery = "recommended_delivery"
        case quietHours = "quiet_hours"
        case hourLocal = "hour_local"
        case needsCount = "needs_count"
        case alertCount = "alert_count"
    }
}

public struct EventTimelineOverview: Codable, Sendable {
    public let events: [EventTimelineItem]
}

public struct EventTimelineItem: Codable, Identifiable, Sendable {
    public let id: String
    public let ts: String
    public let actor: String
    public let surface: String
    public let domain: String
    public let kind: String
    public let severity: String
    public let title: String
    public let detail: String
    public let status: String
    public let source: String
    public let sourceId: String
    public let threadId: String
    public let navigationTarget: String
    public let actions: [String]
    public let trustZone: String
    public let authorityStage: String
    public let whyNow: String

    enum CodingKeys: String, CodingKey {
        case id, ts, actor, surface, domain, kind, severity, title, detail, status, source, actions
        case sourceId = "source_id"
        case threadId = "thread_id"
        case navigationTarget = "navigation_target"
        case trustZone = "trust_zone"
        case authorityStage = "authority_stage"
        case whyNow = "why_now"
    }
}
