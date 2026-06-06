import Foundation

public struct FocusStateOverview: Codable, Sendable {
    public let focusActive: Bool
    public let updatedAt: String
    public let source: String
    public let sourceFresh: Bool
    public let interruptionPosture: FocusInterruptionPosture
    public let suppressionRules: [FocusSuppressionRule]
    public let filter: FocusFilterState
    public let routingLanes: [FocusRoutingLane]
    public let presets: [FocusPreset]
    public let summary: FocusStateSummary

    enum CodingKeys: String, CodingKey {
        case source, summary
        case focusActive = "focus_active"
        case updatedAt = "updated_at"
        case sourceFresh = "source_fresh"
        case interruptionPosture = "interruption_posture"
        case suppressionRules = "suppression_rules"
        case filter
        case routingLanes = "routing_lanes"
        case presets
    }
}

public struct FocusInterruptionPosture: Codable, Sendable {
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

    enum CodingKeys: String, CodingKey {
        case mode, label, reason
        case recommendedDelivery = "recommended_delivery"
        case focusActive = "focus_active"
        case quietHours = "quiet_hours"
        case hourLocal = "hour_local"
        case needsCount = "needs_count"
        case alertCount = "alert_count"
        case presentMembers = "present_members"
        case updatedAt = "updated_at"
    }
}

public struct FocusSuppressionRule: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let detail: String
    public let active: Bool
}

public struct FocusFilterState: Codable, Sendable {
    public let jarvisMode: String
    public let holdApprovals: Bool
    public let silenceBriefings: Bool
    public let source: String

    enum CodingKeys: String, CodingKey {
        case source
        case jarvisMode = "jarvis_mode"
        case holdApprovals = "hold_approvals"
        case silenceBriefings = "silence_briefings"
    }
}

public struct FocusRoutingLane: Codable, Sendable, Identifiable {
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

public struct FocusPreset: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let detail: String
    public let focusActive: Bool
    public let jarvisMode: String
    public let holdApprovals: Bool
    public let silenceBriefings: Bool
    public let active: Bool

    enum CodingKeys: String, CodingKey {
        case id, title, detail, active
        case focusActive = "focus_active"
        case jarvisMode = "jarvis_mode"
        case holdApprovals = "hold_approvals"
        case silenceBriefings = "silence_briefings"
    }
}

public struct FocusStateSummary: Codable, Sendable {
    public let label: String
    public let detail: String
    public let recommendedDelivery: String

    enum CodingKeys: String, CodingKey {
        case label, detail
        case recommendedDelivery = "recommended_delivery"
    }
}

public struct FocusWorkflowActionResult: Codable, Sendable {
    public let requestId: String
    public let status: String
    public let stored: Bool
    public let focusActive: Bool
    public let performedAction: String?
    public let boundaryDecision: String?
    public let boundaryReason: String?
    public let trustZone: String?
    public let authorityStage: String?
    public let arenaStatus: String?
    public let approvalMode: String?

    enum CodingKeys: String, CodingKey {
        case status, stored
        case requestId = "request_id"
        case focusActive = "focus_active"
        case performedAction = "performed_action"
        case boundaryDecision = "boundary_decision"
        case boundaryReason = "boundary_reason"
        case trustZone = "trust_zone"
        case authorityStage = "authority_stage"
        case arenaStatus = "arena_status"
        case approvalMode = "approval_mode"
    }
}
