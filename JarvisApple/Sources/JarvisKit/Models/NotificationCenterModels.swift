import Foundation

public struct NotificationCenterOverview: Codable, Sendable {
    public let notifications: [NotificationCenterItem]
    public let summary: NotificationCenterSummary
    public let routing: NotificationRoutingOverview
    public let eventSummary: NotificationEventSummary

    enum CodingKeys: String, CodingKey {
        case notifications, summary, routing
        case eventSummary = "event_summary"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        notifications = try container.decodeIfPresent([NotificationCenterItem].self, forKey: .notifications) ?? []
        summary = try container.decodeIfPresent(NotificationCenterSummary.self, forKey: .summary)
            ?? NotificationCenterSummary.fromLegacyNotifications(notifications)
        routing = try container.decodeIfPresent(NotificationRoutingOverview.self, forKey: .routing)
            ?? NotificationRoutingOverview.legacyDefault(alertCount: notifications.count)
        eventSummary = try container.decodeIfPresent(NotificationEventSummary.self, forKey: .eventSummary)
            ?? .legacyDefault()
    }
}

public struct NotificationCenterSummary: Codable, Sendable {
    public let total: Int
    public let pending: Int
    public let seen: Int
    public let snoozed: Int
    public let resolved: Int
    public let dismissed: Int
    public let categories: [String: Int]
    public let lastUpdatedAt: String

    enum CodingKeys: String, CodingKey {
        case total, pending, seen, snoozed, resolved, dismissed, categories
        case lastUpdatedAt = "last_updated_at"
    }

    static func fromLegacyNotifications(_ notifications: [NotificationCenterItem]) -> NotificationCenterSummary {
        let categories = notifications.reduce(into: [String: Int]()) { counts, item in
            let key = item.category.isEmpty ? "unknown" : item.category
            counts[key, default: 0] += 1
        }
        let latest = notifications
            .map { $0.updatedAt.isEmpty ? $0.createdAt : $0.updatedAt }
            .first ?? ""
        return NotificationCenterSummary(
            total: notifications.count,
            pending: notifications.filter { $0.status == "pending" }.count,
            seen: notifications.filter { $0.status == "seen" }.count,
            snoozed: notifications.filter { $0.status == "snoozed" }.count,
            resolved: notifications.filter { $0.status == "resolved" }.count,
            dismissed: notifications.filter { $0.status == "dismissed" }.count,
            categories: categories,
            lastUpdatedAt: latest
        )
    }
}

public struct NotificationRoutingOverview: Codable, Sendable {
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
    public let lanes: [NotificationRoutingLane]

    enum CodingKeys: String, CodingKey {
        case mode, label, reason, lanes
        case recommendedDelivery = "recommended_delivery"
        case focusActive = "focus_active"
        case quietHours = "quiet_hours"
        case hourLocal = "hour_local"
        case needsCount = "needs_count"
        case alertCount = "alert_count"
        case presentMembers = "present_members"
        case updatedAt = "updated_at"
    }

    static func legacyDefault(alertCount: Int) -> NotificationRoutingOverview {
        NotificationRoutingOverview(
            mode: "legacy",
            label: "Legacy delivery",
            reason: "The current server has not published routing metadata for Notification Center yet.",
            recommendedDelivery: "badge_only",
            focusActive: false,
            quietHours: false,
            hourLocal: 0,
            needsCount: 0,
            alertCount: alertCount,
            presentMembers: [],
            updatedAt: "",
            lanes: []
        )
    }
}

public struct NotificationRoutingLane: Codable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let detail: String
    public let active: Bool
}

public struct NotificationEventSummary: Codable, Sendable {
    public let recentCount: Int
    public let domains: [String: Int]
    public let severities: [String: Int]
    public let lastEventAt: String

    enum CodingKeys: String, CodingKey {
        case domains, severities
        case recentCount = "recent_count"
        case lastEventAt = "last_event_at"
    }

    static func legacyDefault() -> NotificationEventSummary {
        NotificationEventSummary(
            recentCount: 0,
            domains: [:],
            severities: [:],
            lastEventAt: ""
        )
    }
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

public struct NotificationWorkflowActionResult: Codable, Sendable {
    public let requestId: String
    public let status: String
    public let notification: NotificationCenterItem
    public let performedAction: String?
    public let boundaryDecision: String?
    public let boundaryReason: String?
    public let trustZone: String?
    public let authorityStage: String?
    public let arenaStatus: String?
    public let approvalMode: String?

    enum CodingKeys: String, CodingKey {
        case status, notification
        case requestId = "request_id"
        case performedAction = "performed_action"
        case boundaryDecision = "boundary_decision"
        case boundaryReason = "boundary_reason"
        case trustZone = "trust_zone"
        case authorityStage = "authority_stage"
        case arenaStatus = "arena_status"
        case approvalMode = "approval_mode"
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
