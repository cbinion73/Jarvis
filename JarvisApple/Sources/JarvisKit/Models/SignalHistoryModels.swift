import Foundation

public struct SoundHistoryOverview: Codable, Sendable {
    public let count: Int
    public let recentItems: [SoundHistoryItem]
    public let highConfidenceItems: [SoundHistoryItem]
    public let attentionFlags: [SignalAttentionFlag]

    enum CodingKeys: String, CodingKey {
        case count
        case recentItems = "recent_items"
        case highConfidenceItems = "high_confidence_items"
        case attentionFlags = "attention_flags"
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

    enum CodingKeys: String, CodingKey {
        case count
        case recentItems = "recent_items"
        case recentContexts = "recent_contexts"
        case attentionFlags = "attention_flags"
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
