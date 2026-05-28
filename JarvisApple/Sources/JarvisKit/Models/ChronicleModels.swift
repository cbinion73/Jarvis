import Foundation

// MARK: - ChronicleOverview

/// Recent Chronicle entries returned by GET /api/apple/chronicle
public struct ChronicleOverview: Codable, Sendable {
    public let entries:   [ChronicleEntry]
    public let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case entries
        case updatedAt = "updated_at"
    }
}

// MARK: - ChronicleEntry

public struct ChronicleEntry: Codable, Identifiable, Sendable {
    public let id:        String
    public let type:      String      // "reflection" | "prayer" | "gratitude" | "milestone" | "scripture"
    public let title:     String
    public let body:      String
    public let scripture: String?
    public let timestamp: String
}

// MARK: - FaithOverview

/// Daily word and morning spiritual context returned by GET /api/apple/faith
public struct FaithOverview: Codable, Sendable {
    public let dailyWord:       DailyWord
    public let morningContext:  [String: String]
    public let updatedAt:       String

    enum CodingKeys: String, CodingKey {
        case dailyWord      = "daily_word"
        case morningContext = "morning_context"
        case updatedAt      = "updated_at"
    }
}

// MARK: - DailyWord

public struct DailyWord: Codable, Sendable {
    public let agent:       String
    public let agentTitle:  String
    public let word:        String
    public let passage:     String
    public let domain:      String
    public let generatedAt: String

    enum CodingKeys: String, CodingKey {
        case agent
        case agentTitle  = "agent_title"
        case word, passage, domain
        case generatedAt = "generated_at"
    }
}

// MARK: - ChronicleCapture (request body)

public struct ChronicleCapture: Codable, Sendable {
    public let type:    String
    public let note:    String
    public let actorId: String

    public init(type: String, note: String, actorId: String = "chris") {
        self.type    = type
        self.note    = note
        self.actorId = actorId
    }

    enum CodingKeys: String, CodingKey {
        case type, note
        case actorId = "actor_id"
    }
}
