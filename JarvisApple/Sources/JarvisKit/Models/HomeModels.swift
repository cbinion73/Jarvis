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
    public let homeOps: HomeOpsSummary?
    public let continuity: HomeContinuity?
    public let whileYouWereAway: WhileYouWereAwayReport?
    public let actionItems: [HomeActionItem]

    public init(
        presentMembers: [String],
        doors: [String: String],
        temperature: TemperatureState,
        lightsOn: [String],
        alerts: [HomeAlert],
        homeContext: HomeContext? = nil,
        homeOps: HomeOpsSummary? = nil,
        continuity: HomeContinuity? = nil,
        whileYouWereAway: WhileYouWereAwayReport? = nil,
        actionItems: [HomeActionItem] = []
    ) {
        self.presentMembers = presentMembers
        self.doors = doors
        self.temperature = temperature
        self.lightsOn = lightsOn
        self.alerts = alerts
        self.homeContext = homeContext
        self.homeOps = homeOps
        self.continuity = continuity
        self.whileYouWereAway = whileYouWereAway
        self.actionItems = actionItems
    }

    enum CodingKeys: String, CodingKey {
        case presentMembers = "present_members"
        case doors
        case temperature
        case lightsOn = "lights_on"
        case alerts
        case homeContext = "home_context"
        case homeOps = "home_ops"
        case continuity
        case whileYouWereAway = "while_you_were_away"
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
        homeOps = try container.decodeIfPresent(HomeOpsSummary.self, forKey: .homeOps)
        continuity = try container.decodeIfPresent(HomeContinuity.self, forKey: .continuity)
        whileYouWereAway = try container.decodeIfPresent(WhileYouWereAwayReport.self, forKey: .whileYouWereAway)
        actionItems = try container.decodeIfPresent([HomeActionItem].self, forKey: .actionItems) ?? []
    }
}

public struct HomeContinuity: Codable, Sendable {
    public let subjectDisplayName: String
    public let morningRoom: String
    public let activeMode: String
    public let primaryRooms: [String]
    public let guidanceLines: [String]
    public let profileFactCount: Int
    public let recentProfileFacts: [HomeContinuityFact]
    public let recentFirstLight: [HomeContinuityMoment]
    public let longHorizonLines: [String]
    public let activeThreads: [String]

    enum CodingKeys: String, CodingKey {
        case subjectDisplayName = "subject_display_name"
        case morningRoom = "morning_room"
        case activeMode = "active_mode"
        case primaryRooms = "primary_rooms"
        case guidanceLines = "guidance_lines"
        case profileFactCount = "profile_fact_count"
        case recentProfileFacts = "recent_profile_facts"
        case recentFirstLight = "recent_first_light"
        case longHorizonLines = "long_horizon_lines"
        case activeThreads = "active_threads"
    }
}

public struct HomeContinuityFact: Codable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let summary: String
}

public struct HomeContinuityMoment: Codable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let summary: String
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

public struct HomeOpsSummary: Codable, Sendable {
    public let email: HomeEmailOps
    public let tasks: HomeTaskOps
    public let calendar: HomeCalendarOps
    public let projects: HomeProjectOps
    public let sync: HomeSyncOps
}

public struct HomeEmailOps: Codable, Sendable {
    public let gmailUnread: Int
    public let outlookUnread: Int
    public let totalUnread: Int
    public let flaggedTotal: Int

    enum CodingKeys: String, CodingKey {
        case gmailUnread = "gmail_unread"
        case outlookUnread = "outlook_unread"
        case totalUnread = "total_unread"
        case flaggedTotal = "flagged_total"
    }
}

public struct HomeTaskOps: Codable, Sendable {
    public let openCount: Int
    public let overdueCount: Int
    public let dueTodayCount: Int
    public let dueThisWeekCount: Int
    public let topTitles: [String]

    enum CodingKeys: String, CodingKey {
        case openCount = "open_count"
        case overdueCount = "overdue_count"
        case dueTodayCount = "due_today_count"
        case dueThisWeekCount = "due_this_week_count"
        case topTitles = "top_titles"
    }
}

public struct HomeCalendarOps: Codable, Sendable {
    public let todayCount: Int
    public let upcomingCount: Int
    public let nextTitle: String
    public let nextStart: String
    public let nextLocation: String

    enum CodingKeys: String, CodingKey {
        case todayCount = "today_count"
        case upcomingCount = "upcoming_count"
        case nextTitle = "next_title"
        case nextStart = "next_start"
        case nextLocation = "next_location"
    }
}

public struct HomeProjectOps: Codable, Sendable {
    public let activeCount: Int
    public let stalledCount: Int
    public let totalCount: Int
    public let topTitles: [String]
    public let unclassifiedSignalCount: Int

    enum CodingKeys: String, CodingKey {
        case activeCount = "active_count"
        case stalledCount = "stalled_count"
        case totalCount = "total_count"
        case topTitles = "top_titles"
        case unclassifiedSignalCount = "unclassified_signal_count"
    }
}

public struct HomeSyncOps: Codable, Sendable {
    public let connectedSources: [String]
    public let attentionSources: [String]

    enum CodingKeys: String, CodingKey {
        case connectedSources = "connected_sources"
        case attentionSources = "attention_sources"
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
