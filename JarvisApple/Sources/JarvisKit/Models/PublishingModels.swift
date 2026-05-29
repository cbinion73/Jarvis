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
    public let approvals:  [HuddleApproval]
    public let approvalsCount: Int
    public let totalActiveWork: Int
    public let updatedAt:  String

    enum CodingKeys: String, CodingKey {
        case reports, blockers, highlights, approvals
        case approvalsCount = "approvals_count"
        case totalActiveWork = "total_active_work"
        case updatedAt = "updated_at"
    }

    public init(
        reports: [AgentReport] = [],
        blockers: [String] = [],
        highlights: [String] = [],
        approvals: [HuddleApproval] = [],
        approvalsCount: Int = 0,
        totalActiveWork: Int = 0,
        updatedAt: String = ""
    ) {
        self.reports = reports
        self.blockers = blockers
        self.highlights = highlights
        self.approvals = approvals
        self.approvalsCount = approvalsCount
        self.totalActiveWork = totalActiveWork
        self.updatedAt = updatedAt
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        reports = try container.decodeIfPresent([AgentReport].self, forKey: .reports) ?? []
        blockers = try container.decodeIfPresent([String].self, forKey: .blockers) ?? []
        highlights = try container.decodeIfPresent([String].self, forKey: .highlights) ?? []
        approvals = try container.decodeIfPresent([HuddleApproval].self, forKey: .approvals) ?? []
        approvalsCount = try container.decodeIfPresent(Int.self, forKey: .approvalsCount) ?? approvals.count
        totalActiveWork = try container.decodeIfPresent(Int.self, forKey: .totalActiveWork) ?? 0
        updatedAt = try container.decodeIfPresent(String.self, forKey: .updatedAt) ?? ""
    }
}

// MARK: - AgentReport

public struct AgentReport: Codable, Identifiable, Sendable {
    public let agentId:   String
    public let agentName: String
    public let domain:    String
    public let status:    String   // "ok" | "busy" | "blocked" | "idle"
    public let summary:   String
    public let blockers:  [String]
    public let yesterday: String
    public let today:     String
    public let needs:     String
    public let highlights:[String]
    public let source:    String
    public let activeWorkCount: Int

    public var id: String { agentId }

    enum CodingKeys: String, CodingKey {
        case agentId   = "agent_id"
        case agentName = "agent_name"
        case domain, status, summary, blockers, yesterday, today, needs, highlights, source
        case activeWorkCount = "active_work_count"
    }

    public init(
        agentId: String,
        agentName: String,
        domain: String = "",
        status: String,
        summary: String,
        blockers: [String] = [],
        yesterday: String = "",
        today: String = "",
        needs: String = "",
        highlights: [String] = [],
        source: String = "generated",
        activeWorkCount: Int = 0
    ) {
        self.agentId = agentId
        self.agentName = agentName
        self.domain = domain
        self.status = status
        self.summary = summary
        self.blockers = blockers
        self.yesterday = yesterday
        self.today = today
        self.needs = needs
        self.highlights = highlights
        self.source = source
        self.activeWorkCount = activeWorkCount
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        agentId = try container.decode(String.self, forKey: .agentId)
        agentName = try container.decode(String.self, forKey: .agentName)
        domain = try container.decodeIfPresent(String.self, forKey: .domain) ?? ""
        status = try container.decodeIfPresent(String.self, forKey: .status) ?? "ok"
        summary = try container.decodeIfPresent(String.self, forKey: .summary) ?? ""
        blockers = try container.decodeIfPresent([String].self, forKey: .blockers) ?? []
        yesterday = try container.decodeIfPresent(String.self, forKey: .yesterday) ?? ""
        today = try container.decodeIfPresent(String.self, forKey: .today) ?? ""
        needs = try container.decodeIfPresent(String.self, forKey: .needs) ?? ""
        highlights = try container.decodeIfPresent([String].self, forKey: .highlights) ?? []
        source = try container.decodeIfPresent(String.self, forKey: .source) ?? "generated"
        activeWorkCount = try container.decodeIfPresent(Int.self, forKey: .activeWorkCount) ?? 0
    }
}

public struct HuddleApproval: Codable, Identifiable, Sendable {
    public let workId: String
    public let title: String
    public let agent: String
    public let proposal: String
    public let domain: String

    public var id: String { workId.isEmpty ? "\(agent)-\(title)" : workId }

    enum CodingKeys: String, CodingKey {
        case workId = "work_id"
        case title, agent, proposal, domain
    }
}
