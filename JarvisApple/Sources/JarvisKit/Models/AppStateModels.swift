import Foundation

public struct AppStateOverview: Codable, Sendable {
    public let server: AppStateServer
    public let calendar: AppStateCalendar
    public let reminders: AppStateReminders
    public let focus: AppStateFocus
    public let notifications: AppStateNotifications
    public let nowPlaying: AppStateNowPlaying
    public let soundAlert: AppStateSignal
    public let visionScan: AppStateVisionScan
    public let presence: AppStatePresence
    public let syncHealth: AppStateSyncHealth

    enum CodingKeys: String, CodingKey {
        case server, calendar, reminders, focus, notifications, presence
        case nowPlaying = "now_playing"
        case soundAlert = "sound_alert"
        case visionScan = "vision_scan"
        case syncHealth = "sync_health"
    }
}

public struct AppStateServer: Codable, Sendable {
    public let mode: String
    public let needsCount: Int
    public let drift: Bool
    public let weather: String
    public let ts: String

    enum CodingKeys: String, CodingKey {
        case mode, drift, weather, ts
        case needsCount = "needs_count"
    }
}

public struct AppStateCalendar: Codable, Sendable {
    public let synced: Bool
    public let count: Int
    public let syncedAt: String
    public let nextItems: [AppStateCalendarItem]

    enum CodingKeys: String, CodingKey {
        case synced, count
        case syncedAt = "synced_at"
        case nextItems = "next_items"
    }
}

public struct AppStateCalendarItem: Codable, Sendable, Identifiable {
    public var id: String { "\(title)|\(start)|\(calendar)" }
    public let title: String
    public let start: String
    public let end: String
    public let location: String
    public let calendar: String
}

public struct AppStateReminders: Codable, Sendable {
    public let synced: Bool
    public let count: Int
    public let syncedAt: String
    public let topItems: [AppStateReminderItem]

    enum CodingKeys: String, CodingKey {
        case synced, count
        case syncedAt = "synced_at"
        case topItems = "top_items"
    }
}

public struct AppStateReminderItem: Codable, Sendable, Identifiable {
    public var id: String { "\(title)|\(due)|\(list)" }
    public let title: String
    public let due: String
    public let list: String
    public let priority: Int
}

public struct AppStateFocus: Codable, Sendable {
    public let focusActive: Bool
    public let updatedAt: String
    public let source: String

    enum CodingKeys: String, CodingKey {
        case source
        case focusActive = "focus_active"
        case updatedAt = "updated_at"
    }
}

public struct AppStateNotifications: Codable, Sendable {
    public let pendingCount: Int
    public let recent: [PendingNotification]

    enum CodingKeys: String, CodingKey {
        case recent
        case pendingCount = "pending_count"
    }
}

public struct AppStateNowPlaying: Codable, Sendable {
    public let title: String
    public let artist: String
    public let album: String
    public let isPlaying: Bool
    public let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case title, artist, album
        case isPlaying = "is_playing"
        case updatedAt = "updated_at"
    }
}

public struct AppStateSignal: Codable, Sendable {
    public let label: String
    public let confidence: Double?
    public let source: String
    public let receivedAt: String

    enum CodingKeys: String, CodingKey {
        case label, confidence, source
        case receivedAt = "received_at"
    }
}

public struct AppStateVisionScan: Codable, Sendable {
    public let context: String
    public let source: String
    public let textPreview: String
    public let receivedAt: String

    enum CodingKeys: String, CodingKey {
        case context, source
        case textPreview = "text_preview"
        case receivedAt = "received_at"
    }
}

public struct AppStatePresence: Codable, Sendable {
    public let presentMembers: [String]
    public let lightsOnCount: Int
    public let alertCount: Int

    enum CodingKeys: String, CodingKey {
        case presentMembers = "present_members"
        case lightsOnCount = "lights_on_count"
        case alertCount = "alert_count"
    }
}

public struct AppStateSyncHealth: Codable, Sendable {
    public let calendar: AppStateSyncDomain
    public let reminders: AppStateSyncDomain
    public let focus: AppStateSyncDomain
    public let nowPlaying: AppStateSyncDomain
    public let soundAlert: AppStateSyncDomain
    public let visionScan: AppStateSyncDomain

    enum CodingKeys: String, CodingKey {
        case calendar, reminders, focus
        case nowPlaying = "now_playing"
        case soundAlert = "sound_alert"
        case visionScan = "vision_scan"
    }
}

public struct AppStateSyncDomain: Codable, Sendable {
    public let synced: Bool
    public let syncedAt: String?

    enum CodingKeys: String, CodingKey {
        case synced
        case syncedAt = "synced_at"
    }
}
