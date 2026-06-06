import Foundation

public struct SystemsProfileSettings: Codable, Sendable {
    public let subjectUserId: String
    public let notifications: SystemsProfileNotificationSettings
    public let privacy: SystemsProfilePrivacySettings
    public let dashboard: SystemsProfileDashboardSettings
    public let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case notifications, privacy, dashboard
        case subjectUserId = "subject_user_id"
        case updatedAt = "updated_at"
    }

    public init(
        subjectUserId: String,
        notifications: SystemsProfileNotificationSettings,
        privacy: SystemsProfilePrivacySettings,
        dashboard: SystemsProfileDashboardSettings,
        updatedAt: String
    ) {
        self.subjectUserId = subjectUserId
        self.notifications = notifications
        self.privacy = privacy
        self.dashboard = dashboard
        self.updatedAt = updatedAt
    }
}

public struct SystemsProfileNotificationSettings: Codable, Sendable {
    public let approvals: Bool
    public let healthAlerts: Bool
    public let calendarReminders: Bool
    public let agentUpdates: Bool

    enum CodingKeys: String, CodingKey {
        case approvals
        case healthAlerts = "health_alerts"
        case calendarReminders = "calendar_reminders"
        case agentUpdates = "agent_updates"
    }

    public init(approvals: Bool, healthAlerts: Bool, calendarReminders: Bool, agentUpdates: Bool) {
        self.approvals = approvals
        self.healthAlerts = healthAlerts
        self.calendarReminders = calendarReminders
        self.agentUpdates = agentUpdates
    }
}

public struct SystemsProfilePrivacySettings: Codable, Sendable {
    public let shareHealthWithFamily: Bool
    public let shareCalendarWithFamily: Bool
    public let privateChronicle: Bool

    enum CodingKeys: String, CodingKey {
        case shareHealthWithFamily = "share_health_with_family"
        case shareCalendarWithFamily = "share_calendar_with_family"
        case privateChronicle = "private_chronicle"
    }

    public init(shareHealthWithFamily: Bool, shareCalendarWithFamily: Bool, privateChronicle: Bool) {
        self.shareHealthWithFamily = shareHealthWithFamily
        self.shareCalendarWithFamily = shareCalendarWithFamily
        self.privateChronicle = privateChronicle
    }
}

public struct SystemsProfileDashboardSettings: Codable, Sendable {
    public let showHealth: Bool
    public let showFinance: Bool
    public let showDining: Bool
    public let showChronicle: Bool
    public let showPublishing: Bool

    enum CodingKeys: String, CodingKey {
        case showHealth = "show_health"
        case showFinance = "show_finance"
        case showDining = "show_dining"
        case showChronicle = "show_chronicle"
        case showPublishing = "show_publishing"
    }

    public init(showHealth: Bool, showFinance: Bool, showDining: Bool, showChronicle: Bool, showPublishing: Bool) {
        self.showHealth = showHealth
        self.showFinance = showFinance
        self.showDining = showDining
        self.showChronicle = showChronicle
        self.showPublishing = showPublishing
    }
}

public struct SystemsProfileSettingsActionResult: Codable, Sendable {
    public let message: String
    public let settings: SystemsProfileSettings
    public let focus: SystemsProfileFocus?

    public init(message: String, settings: SystemsProfileSettings, focus: SystemsProfileFocus?) {
        self.message = message
        self.settings = settings
        self.focus = focus
    }
}

public struct SystemsProfileFocus: Codable, Sendable {
    public let module: String
    public let reason: String
    public let route: String
    public let savedAt: String

    enum CodingKeys: String, CodingKey {
        case module, reason, route
        case savedAt = "saved_at"
    }

    public init(module: String, reason: String, route: String, savedAt: String) {
        self.module = module
        self.reason = reason
        self.route = route
        self.savedAt = savedAt
    }
}
