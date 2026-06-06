import Foundation

public struct ReminderWorkflowOverview: Codable, Sendable {
    public let synced: Bool
    public let syncedAt: String
    public let count: Int
    public let summary: ReminderWorkflowSummary
    public let listSummaries: [ReminderListSummary]
    public let openItems: [ReminderWorkflowItem]
    public let overdueItems: [ReminderWorkflowItem]
    public let dueSoonItems: [ReminderWorkflowItem]
    public let priorityItems: [ReminderWorkflowItem]
    public let attentionFlags: [ReminderAttentionFlag]

    enum CodingKeys: String, CodingKey {
        case synced, count
        case syncedAt = "synced_at"
        case summary
        case listSummaries = "list_summaries"
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
    public let completed: Bool?
    public let availableActions: [String]

    enum CodingKeys: String, CodingKey {
        case id, title, due, list, priority, notes, overdue, completed
        case priorityLabel = "priority_label"
        case minutesAway = "minutes_away"
        case dueSoon = "due_soon"
        case availableActions = "available_actions"
    }
}

public struct ReminderWorkflowSummary: Codable, Sendable {
    public let openCount: Int
    public let overdueCount: Int
    public let dueSoonCount: Int
    public let priorityCount: Int
    public let noDueDateCount: Int

    enum CodingKeys: String, CodingKey {
        case openCount = "open_count"
        case overdueCount = "overdue_count"
        case dueSoonCount = "due_soon_count"
        case priorityCount = "priority_count"
        case noDueDateCount = "no_due_date_count"
    }
}

public struct ReminderListSummary: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let count: Int
    public let overdueCount: Int
    public let dueSoonCount: Int
    public let priorityCount: Int

    enum CodingKeys: String, CodingKey {
        case id, title, count
        case overdueCount = "overdue_count"
        case dueSoonCount = "due_soon_count"
        case priorityCount = "priority_count"
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

public struct ReminderWorkflowActionResult: Codable, Sendable {
    public let requestId: String
    public let status: String
    public let reminder: ReminderWorkflowItem
    public let performedAction: String?
    public let boundaryDecision: String?
    public let boundaryReason: String?
    public let trustZone: String?
    public let authorityStage: String?
    public let arenaStatus: String?
    public let approvalMode: String?

    enum CodingKeys: String, CodingKey {
        case status, reminder
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
