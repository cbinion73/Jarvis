import Foundation

// MARK: - PublishOverview

/// Publishing dashboard returned by GET /api/apple/publishing
public struct PublishOverview: Codable, Sendable {
    public let projects:       [PublishProject]
    public let revenueSummary: RevenueSummary
    public let upcoming:       [CalendarItem]
    public let pendingReviews: [PublishReview]
    public let pendingReviewsCount: Int
    public let launchControl: PublishLaunchControl?
    public let actionItems: [PublishActionItem]
    public let updatedAt:      String

    enum CodingKeys: String, CodingKey {
        case projects
        case revenueSummary = "revenue_summary"
        case upcoming
        case pendingReviews = "pending_reviews"
        case pendingReviewsCount = "pending_reviews_count"
        case launchControl = "launch_control"
        case actionItems = "action_items"
        case updatedAt      = "updated_at"
    }

    public init(
        projects: [PublishProject] = [],
        revenueSummary: RevenueSummary = RevenueSummary(monthlyEstimate: 0, streamCount: 0, streams: []),
        upcoming: [CalendarItem] = [],
        pendingReviews: [PublishReview] = [],
        pendingReviewsCount: Int = 0,
        launchControl: PublishLaunchControl? = nil,
        actionItems: [PublishActionItem] = [],
        updatedAt: String = ""
    ) {
        self.projects = projects
        self.revenueSummary = revenueSummary
        self.upcoming = upcoming
        self.pendingReviews = pendingReviews
        self.pendingReviewsCount = pendingReviewsCount
        self.launchControl = launchControl
        self.actionItems = actionItems
        self.updatedAt = updatedAt
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        projects = try container.decodeIfPresent([PublishProject].self, forKey: .projects) ?? []
        revenueSummary = try container.decodeIfPresent(RevenueSummary.self, forKey: .revenueSummary) ?? RevenueSummary(monthlyEstimate: 0, streamCount: 0, streams: [])
        upcoming = try container.decodeIfPresent([CalendarItem].self, forKey: .upcoming) ?? []
        pendingReviews = try container.decodeIfPresent([PublishReview].self, forKey: .pendingReviews) ?? []
        pendingReviewsCount = try container.decodeIfPresent(Int.self, forKey: .pendingReviewsCount) ?? pendingReviews.count
        launchControl = try container.decodeIfPresent(PublishLaunchControl.self, forKey: .launchControl)
        actionItems = try container.decodeIfPresent([PublishActionItem].self, forKey: .actionItems) ?? []
        updatedAt = try container.decodeIfPresent(String.self, forKey: .updatedAt) ?? ""
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
    public let description: String
    public let notes: String
    public let updatedAt: String

    public var id: String { projectId }

    enum CodingKeys: String, CodingKey {
        case projectId = "project_id"
        case title, type, status, platform, url, description, notes
        case updatedAt = "updated_at"
    }

    public init(
        projectId: String,
        title: String,
        type: String,
        status: String,
        platform: String,
        url: String? = nil,
        description: String = "",
        notes: String = "",
        updatedAt: String = ""
    ) {
        self.projectId = projectId
        self.title = title
        self.type = type
        self.status = status
        self.platform = platform
        self.url = url
        self.description = description
        self.notes = notes
        self.updatedAt = updatedAt
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        projectId = try container.decodeIfPresent(String.self, forKey: .projectId) ?? UUID().uuidString
        title = try container.decodeIfPresent(String.self, forKey: .title) ?? ""
        type = try container.decodeIfPresent(String.self, forKey: .type) ?? ""
        status = try container.decodeIfPresent(String.self, forKey: .status) ?? ""
        platform = try container.decodeIfPresent(String.self, forKey: .platform) ?? ""
        url = try container.decodeIfPresent(String.self, forKey: .url)
        description = try container.decodeIfPresent(String.self, forKey: .description) ?? ""
        notes = try container.decodeIfPresent(String.self, forKey: .notes) ?? ""
        updatedAt = try container.decodeIfPresent(String.self, forKey: .updatedAt) ?? ""
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

    public init(monthlyEstimate: Double, streamCount: Int, streams: [RevenueStream]) {
        self.monthlyEstimate = monthlyEstimate
        self.streamCount = streamCount
        self.streams = streams
    }
}

public struct PublishReview: Codable, Identifiable, Sendable {
    public let reviewId: String
    public let title: String
    public let slug: String
    public let stageKey: String
    public let stageDisplay: String
    public let contentPreview: String
    public let wordCount: Int
    public let readySince: String
    public let approvalId: String

    public var id: String { reviewId }

    enum CodingKeys: String, CodingKey {
        case reviewId = "review_id"
        case title, slug
        case stageKey = "stage_key"
        case stageDisplay = "stage_display"
        case contentPreview = "content_preview"
        case wordCount = "word_count"
        case readySince = "ready_since"
        case approvalId = "approval_id"
    }
}

public struct PublishLaunchControl: Codable, Sendable {
    public let projectId: String
    public let title: String
    public let platform: String
    public let status: String
    public let phase: String
    public let daysToLaunch: Int?
    public let postsScheduled: Int
    public let postsPendingApproval: Int
    public let launchDate: String
    public let nextAction: String

    enum CodingKeys: String, CodingKey {
        case projectId = "project_id"
        case title, platform, status, phase
        case daysToLaunch = "days_to_launch"
        case postsScheduled = "posts_scheduled"
        case postsPendingApproval = "posts_pending_approval"
        case launchDate = "launch_date"
        case nextAction = "next_action"
    }
}

public struct PublishActionItem: Codable, Identifiable, Sendable {
    public let title: String
    public let detail: String
    public let kind: String
    public let priority: String

    public var id: String { "\(kind)-\(title)" }
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
