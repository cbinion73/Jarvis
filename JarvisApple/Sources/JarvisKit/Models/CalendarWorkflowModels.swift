import Foundation

public struct CalendarWorkflowOverview: Codable, Sendable {
    public let synced: Bool
    public let syncedAt: String
    public let count: Int
    public let nextEvents: [CalendarWorkflowEvent]
    public let todayEvents: [CalendarWorkflowEvent]
    public let routeSensitiveEvents: [CalendarWorkflowEvent]
    public let preparationCues: [CalendarPreparationCue]
    public let attentionFlags: [CalendarAttentionFlag]

    enum CodingKeys: String, CodingKey {
        case synced, count
        case syncedAt = "synced_at"
        case nextEvents = "next_events"
        case todayEvents = "today_events"
        case routeSensitiveEvents = "route_sensitive_events"
        case preparationCues = "preparation_cues"
        case attentionFlags = "attention_flags"
    }
}

public struct CalendarWorkflowEvent: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let start: String
    public let end: String
    public let location: String
    public let calendar: String
    public let notes: String
    public let url: String
    public let allDay: Bool
    public let minutesAway: Int?
    public let prepWindowOpen: Bool
    public let routeReady: Bool

    enum CodingKeys: String, CodingKey {
        case id, title, start, end, location, calendar, notes, url
        case allDay = "all_day"
        case minutesAway = "minutes_away"
        case prepWindowOpen = "prep_window_open"
        case routeReady = "route_ready"
    }
}

public struct CalendarPreparationCue: Codable, Sendable, Identifiable {
    public var id: String { eventId }
    public let eventId: String
    public let title: String
    public let detail: String
    public let action: String
    public let start: String
    public let location: String

    enum CodingKeys: String, CodingKey {
        case title, detail, action, start, location
        case eventId = "event_id"
    }
}

public struct CalendarAttentionFlag: Codable, Sendable, Identifiable {
    public let id: String
    public let eventId: String
    public let kind: String
    public let severity: String
    public let title: String
    public let detail: String

    enum CodingKeys: String, CodingKey {
        case id, kind, severity, title, detail
        case eventId = "event_id"
    }
}

public struct CalendarRouteActionResult: Codable, Sendable {
    public let requestId: String
    public let status: String
    public let eventId: String
    public let title: String
    public let location: String
    public let mapsURL: String
    public let boundaryDecision: String?
    public let boundaryReason: String?
    public let trustZone: String?
    public let authorityStage: String?
    public let arenaStatus: String?
    public let approvalMode: String?

    enum CodingKeys: String, CodingKey {
        case status, title, location
        case requestId = "request_id"
        case eventId = "event_id"
        case mapsURL = "maps_url"
        case boundaryDecision = "boundary_decision"
        case boundaryReason = "boundary_reason"
        case trustZone = "trust_zone"
        case authorityStage = "authority_stage"
        case arenaStatus = "arena_status"
        case approvalMode = "approval_mode"
    }
}
