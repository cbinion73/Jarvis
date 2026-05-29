import Foundation

public struct ReminderWorkflowOverview: Codable, Sendable {
    public let synced: Bool
    public let syncedAt: String
    public let count: Int
    public let openItems: [ReminderWorkflowItem]
    public let overdueItems: [ReminderWorkflowItem]
    public let dueSoonItems: [ReminderWorkflowItem]
    public let priorityItems: [ReminderWorkflowItem]
    public let attentionFlags: [ReminderAttentionFlag]

    enum CodingKeys: String, CodingKey {
        case synced, count
        case syncedAt = "synced_at"
        case openItems = "open_items"
        case overdueItems = "overdue_items"
        case dueSoonItems = "due_soon_items"
        case priorityItems = "priority_items"
        case attentionFlags = "attention_flags"
    }
}

public struct ReminderWorkflowItem: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let due: String
    public let list: String
    public let priority: Int
    public let priorityLabel: String
    public let notes: String
    public let minutesAway: Int?
    public let overdue: Bool
    public let dueSoon: Bool
    public let availableActions: [String]

    enum CodingKeys: String, CodingKey {
        case id, title, due, list, priority, notes, overdue
        case priorityLabel = "priority_label"
        case minutesAway = "minutes_away"
        case dueSoon = "due_soon"
        case availableActions = "available_actions"
    }
}

public struct ReminderAttentionFlag: Codable, Sendable, Identifiable {
    public let id: String
    public let reminderId: String
    public let kind: String
    public let severity: String
    public let title: String
    public let detail: String

    enum CodingKeys: String, CodingKey {
        case id, kind, severity, title, detail
        case reminderId = "reminder_id"
    }
}
