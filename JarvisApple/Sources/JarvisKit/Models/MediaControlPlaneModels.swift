import Foundation

public struct NowPlayingStateOverview: Codable, Sendable {
    public let title: String
    public let artist: String
    public let album: String
    public let isPlaying: Bool
    public let updatedAt: String
    public let artworkAvailable: Bool
    public let summary: NowPlayingSummary
    public let routingRules: [NowPlayingRoutingRule]
    public let responsePlans: [NowPlayingResponsePlan]
    public let suggestedControls: [NowPlayingSuggestedControl]
    public let recentItems: [NowPlayingHistoryItem]

    enum CodingKeys: String, CodingKey {
        case title, artist, album
        case isPlaying = "is_playing"
        case updatedAt = "updated_at"
        case artworkAvailable = "artwork_available"
        case summary
        case routingRules = "routing_rules"
        case responsePlans = "response_plans"
        case suggestedControls = "suggested_controls"
        case recentItems = "recent_items"
    }
}

public struct NowPlayingSummary: Codable, Sendable {
    public let label: String
    public let detail: String
}

public struct NowPlayingRoutingRule: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let detail: String
    public let deliveryMode: String
    public let active: Bool

    enum CodingKeys: String, CodingKey {
        case id, title, detail, active
        case deliveryMode = "delivery_mode"
    }
}

public struct NowPlayingResponsePlan: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let detail: String
    public let target: String
    public let priority: String
    public let active: Bool
}

public struct NowPlayingSuggestedControl: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let detail: String
    public let style: String
    public let active: Bool
}

public struct NowPlayingHistoryItem: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let detail: String
    public let ts: String
    public let isPlaying: Bool
    public let artist: String
    public let album: String

    enum CodingKeys: String, CodingKey {
        case id, title, detail, ts, artist, album
        case isPlaying = "is_playing"
    }
}

public struct ControlPlaneOverview: Codable, Sendable {
    public let notifications: ControlPlaneNotifications
    public let events: ControlPlaneEvents
    public let media: ControlPlaneMedia
    public let freshness: [ControlPlaneFreshnessItem]
}

public struct ControlPlaneNotifications: Codable, Sendable {
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
}

public struct ControlPlaneEvents: Codable, Sendable {
    public let recentCount: Int
    public let domains: [String: Int]
    public let severities: [String: Int]
    public let lastEventAt: String
    public let recentItems: [ControlPlaneEventItem]

    enum CodingKeys: String, CodingKey {
        case domains, severities
        case recentCount = "recent_count"
        case lastEventAt = "last_event_at"
        case recentItems = "recent_items"
    }
}

public struct ControlPlaneMedia: Codable, Sendable {
    public let synced: Bool
    public let updatedAt: String
    public let title: String
    public let isPlaying: Bool

    enum CodingKeys: String, CodingKey {
        case synced, title
        case updatedAt = "updated_at"
        case isPlaying = "is_playing"
    }
}

public struct ControlPlaneFreshnessItem: Codable, Sendable, Identifiable {
    public let id: String
    public let label: String
    public let synced: Bool
    public let updatedAt: String
    public let status: String
    public let detail: String

    enum CodingKeys: String, CodingKey {
        case id, label, synced, status, detail
        case updatedAt = "updated_at"
    }
}

public struct ControlPlaneEventItem: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let detail: String
    public let domain: String
    public let severity: String
    public let ts: String
}
