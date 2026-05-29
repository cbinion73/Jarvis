import Foundation

public struct NowPlayingStateOverview: Codable, Sendable {
    public let title: String
    public let artist: String
    public let album: String
    public let isPlaying: Bool
    public let updatedAt: String
    public let artworkAvailable: Bool
    public let recentItems: [NowPlayingHistoryItem]

    enum CodingKeys: String, CodingKey {
        case title, artist, album
        case isPlaying = "is_playing"
        case updatedAt = "updated_at"
        case artworkAvailable = "artwork_available"
        case recentItems = "recent_items"
    }
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

    enum CodingKeys: String, CodingKey {
        case domains, severities
        case recentCount = "recent_count"
        case lastEventAt = "last_event_at"
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
