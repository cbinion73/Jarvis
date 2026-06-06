import Foundation

public struct SoundHistoryOverview: Codable, Sendable {
    public let count: Int
    public let recentItems: [SoundHistoryItem]
    public let highConfidenceItems: [SoundHistoryItem]
    public let attentionFlags: [SignalAttentionFlag]
    public let policyRules: [SoundPolicyRule]
    public let responsePlans: [SoundResponsePlan]

    enum CodingKeys: String, CodingKey {
        case count
        case recentItems = "recent_items"
        case highConfidenceItems = "high_confidence_items"
        case attentionFlags = "attention_flags"
        case policyRules = "policy_rules"
        case responsePlans = "response_plans"
    }
}

public struct SoundHistoryItem: Codable, Sendable, Identifiable {
    public let id: String
    public let label: String
    public let detail: String
    public let source: String
    public let confidence: Double?
    public let receivedAt: String
    public let resolved: Bool
    public let resolvedAt: String

    enum CodingKeys: String, CodingKey {
        case id, label, detail, source, confidence, resolved
        case receivedAt = "received_at"
        case resolvedAt = "resolved_at"
    }
}

public struct VisionHistoryOverview: Codable, Sendable {
    public let count: Int
    public let recentItems: [VisionHistoryItem]
    public let recentContexts: [String]
    public let attentionFlags: [SignalAttentionFlag]
    public let policyRules: [SoundPolicyRule]
    public let responsePlans: [SoundResponsePlan]

    enum CodingKeys: String, CodingKey {
        case count
        case recentItems = "recent_items"
        case recentContexts = "recent_contexts"
        case attentionFlags = "attention_flags"
        case policyRules = "policy_rules"
        case responsePlans = "response_plans"
    }
}

public struct VisionHistoryItem: Codable, Sendable, Identifiable {
    public let id: String
    public let context: String
    public let source: String
    public let textPreview: String
    public let receivedAt: String
    public let resolved: Bool
    public let resolvedAt: String

    enum CodingKeys: String, CodingKey {
        case id, context, source, resolved
        case textPreview = "text_preview"
        case receivedAt = "received_at"
        case resolvedAt = "resolved_at"
    }
}

public struct SignalAttentionFlag: Codable, Sendable, Identifiable {
    public let id: String
    public let kind: String
    public let severity: String
    public let title: String
    public let detail: String
}

public struct SoundPolicyRule: Codable, Sendable, Identifiable {
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

public struct SoundResponsePlan: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let detail: String
    public let target: String
    public let priority: String
    public let active: Bool

    enum CodingKeys: String, CodingKey {
        case id, title, detail, target, priority, active
    }
}

public struct SignalResolutionActionResult: Codable, Sendable {
    public let requestId: String
    public let status: String
    public let id: String
    public let resolvedAt: String
    public let boundaryDecision: String?
    public let boundaryReason: String?
    public let trustZone: String?
    public let authorityStage: String?
    public let arenaStatus: String?
    public let approvalMode: String?

    enum CodingKeys: String, CodingKey {
        case status, id
        case requestId = "request_id"
        case resolvedAt = "resolved_at"
        case boundaryDecision = "boundary_decision"
        case boundaryReason = "boundary_reason"
        case trustZone = "trust_zone"
        case authorityStage = "authority_stage"
        case arenaStatus = "arena_status"
        case approvalMode = "approval_mode"
    }
}
