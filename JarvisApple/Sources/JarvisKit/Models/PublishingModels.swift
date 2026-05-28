import Foundation

// MARK: - PublishOverview

/// Publishing dashboard returned by GET /api/apple/publishing
public struct PublishOverview: Codable, Sendable {
    public let projects:       [PublishProject]
    public let revenueSummary: RevenueSummary
    public let upcoming:       [CalendarItem]
    public let updatedAt:      String

    enum CodingKeys: String, CodingKey {
        case projects
        case revenueSummary = "revenue_summary"
        case upcoming
        case updatedAt      = "updated_at"
    }
}

// MARK: - PublishProject

public struct PublishProject: Codable, Identifiable, Sendable {
    public let projectId: String
    public let title:     String
    public let type:      String     // "book" | "course" | "blog_post" | "social_campaign"
    public let status:    String     // "draft" | "editing" | "ready" | "published"
    public let platform:  String
    public let url:       String?

    public var id: String { projectId }

    enum CodingKeys: String, CodingKey {
        case projectId = "project_id"
        case title, type, status, platform, url
    }
}

// MARK: - RevenueSummary

public struct RevenueSummary: Codable, Sendable {
    public let monthlyEstimate: Double
    public let streamCount:     Int
    public let streams:         [RevenueStream]

    enum CodingKeys: String, CodingKey {
        case monthlyEstimate = "monthly_estimate"
        case streamCount     = "stream_count"
        case streams
    }
}

// MARK: - RevenueStream

public struct RevenueStream: Codable, Identifiable, Sendable {
    public let streamId:   String
    public let type:       String
    public let source:     String
    public let monthlyEst: Double

    public var id: String { streamId }

    enum CodingKeys: String, CodingKey {
        case streamId  = "stream_id"
        case type, source
        case monthlyEst = "monthly_est"
    }
}

// MARK: - CalendarItem

public struct CalendarItem: Codable, Identifiable, Sendable {
    public let itemId:      String
    public let title:       String
    public let contentType: String
    public let platform:    String
    public let plannedDate: String
    public let status:      String

    public var id: String { itemId }

    enum CodingKeys: String, CodingKey {
        case itemId      = "item_id"
        case title
        case contentType = "content_type"
        case platform
        case plannedDate = "planned_date"
        case status
    }
}

// MARK: - HuddleOverview

/// Agent standup overview returned by GET /api/apple/huddle
public struct HuddleOverview: Codable, Sendable {
    public let reports:    [AgentReport]
    public let blockers:   [String]
    public let highlights: [String]
    public let updatedAt:  String

    enum CodingKeys: String, CodingKey {
        case reports, blockers, highlights
        case updatedAt = "updated_at"
    }
}

// MARK: - AgentReport

public struct AgentReport: Codable, Identifiable, Sendable {
    public let agentId:   String
    public let agentName: String
    public let status:    String   // "ok" | "busy" | "blocked" | "idle"
    public let summary:   String
    public let blockers:  [String]

    public var id: String { agentId }

    enum CodingKeys: String, CodingKey {
        case agentId   = "agent_id"
        case agentName = "agent_name"
        case status, summary, blockers
    }
}
