import Foundation

// MARK: - HomeState

/// Full house state returned by GET /api/apple/home/state
public struct HomeState: Codable, Sendable {
    public let presentMembers: [String]
    public let doors: [String: String]
    public let temperature: TemperatureState
    public let lightsOn: [String]
    public let alerts: [HomeAlert]
    public let homeContext: HomeContext?
    public let actionItems: [HomeActionItem]

    public init(
        presentMembers: [String],
        doors: [String: String],
        temperature: TemperatureState,
        lightsOn: [String],
        alerts: [HomeAlert],
        homeContext: HomeContext? = nil,
        actionItems: [HomeActionItem] = []
    ) {
        self.presentMembers = presentMembers
        self.doors = doors
        self.temperature = temperature
        self.lightsOn = lightsOn
        self.alerts = alerts
        self.homeContext = homeContext
        self.actionItems = actionItems
    }

    enum CodingKeys: String, CodingKey {
        case presentMembers = "present_members"
        case doors
        case temperature
        case lightsOn = "lights_on"
        case alerts
        case homeContext = "home_context"
        case actionItems = "action_items"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        presentMembers = try container.decode([String].self, forKey: .presentMembers)
        doors = try container.decode([String: String].self, forKey: .doors)
        temperature = try container.decode(TemperatureState.self, forKey: .temperature)
        lightsOn = try container.decode([String].self, forKey: .lightsOn)
        alerts = try container.decode([HomeAlert].self, forKey: .alerts)
        homeContext = try container.decodeIfPresent(HomeContext.self, forKey: .homeContext)
        actionItems = try container.decodeIfPresent([HomeActionItem].self, forKey: .actionItems) ?? []
    }
}

public struct HomeActionItem: Codable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let detail: String
    public let command: String
    public let entityId: String
    public let service: String
    public let emphasis: String

    enum CodingKeys: String, CodingKey {
        case id, title, detail, command, service, emphasis
        case entityId = "entity_id"
    }
}

public struct HomeContext: Codable, Sendable {
    public let agenda: HomeAgendaContext
    public let attention: HomeAttentionContext
    public let projects: HomeProjectsContext
}

public struct HomeAgendaContext: Codable, Sendable {
    public let todayEventCount: Int
    public let nextEventTitle: String
    public let nextEventStart: String
    public let nextEventLocation: String

    enum CodingKeys: String, CodingKey {
        case todayEventCount = "today_event_count"
        case nextEventTitle = "next_event_title"
        case nextEventStart = "next_event_start"
        case nextEventLocation = "next_event_location"
    }
}

public struct HomeAttentionContext: Codable, Sendable {
    public let reminderCount: Int
    public let notificationCount: Int
    public let unreadEmailCount: Int
    public let needsCount: Int
    public let focusActive: Bool

    enum CodingKeys: String, CodingKey {
        case reminderCount = "reminder_count"
        case notificationCount = "notification_count"
        case unreadEmailCount = "unread_email_count"
        case needsCount = "needs_count"
        case focusActive = "focus_active"
    }
}

public struct HomeProjectsContext: Codable, Sendable {
    public let publishingProjectCount: Int
    public let activeWorkItemsCount: Int
    public let topTitles: [String]

    enum CodingKeys: String, CodingKey {
        case publishingProjectCount = "publishing_project_count"
        case activeWorkItemsCount = "active_work_items_count"
        case topTitles = "top_titles"
    }
}

// MARK: - TemperatureState

public struct TemperatureState: Codable, Sendable {
    public let inside: Double
    public let target: Double
    /// "cool" | "heat" | "auto" | "off"
    public let mode: String

    public init(inside: Double, target: Double, mode: String) {
        self.inside = inside
        self.target = target
        self.mode = mode
    }
}

// MARK: - HomeAlert

public struct HomeAlert: Codable, Sendable {
    public let entity: String
    public let state: String
    public let message: String

    public init(entity: String, state: String, message: String) {
        self.entity = entity
        self.state = state
        self.message = message
    }
}

// MARK: - HomeCommand

/// Command body for POST /api/apple/home/command
public struct HomeCommand: Codable, Sendable {
    public let command: String
    public let entityId: String
    public let service: String

    public init(command: String, entityId: String, service: String) {
        self.command = command
        self.entityId = entityId
        self.service = service
    }

    enum CodingKeys: String, CodingKey {
        case command
        case entityId = "entity_id"
        case service
    }
}

// MARK: - PresenceEvent

public enum PresenceEvent: String, Codable, Sendable {
    case arrivedHome = "arrived_home"
    case leftHome = "left_home"
}
