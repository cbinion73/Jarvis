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
    public let launchWorkspace: PublishLaunchWorkspace?
    public let actionItems: [PublishActionItem]
    public let continuity: PublishContinuity?
    public let updatedAt:      String

    enum CodingKeys: String, CodingKey {
        case projects
        case revenueSummary = "revenue_summary"
        case upcoming
        case pendingReviews = "pending_reviews"
        case pendingReviewsCount = "pending_reviews_count"
        case launchControl = "launch_control"
        case launchWorkspace = "launch_workspace"
        case actionItems = "action_items"
        case continuity
        case updatedAt      = "updated_at"
    }

    public init(
        projects: [PublishProject] = [],
        revenueSummary: RevenueSummary = RevenueSummary(monthlyEstimate: 0, streamCount: 0, streams: []),
        upcoming: [CalendarItem] = [],
        pendingReviews: [PublishReview] = [],
        pendingReviewsCount: Int = 0,
        launchControl: PublishLaunchControl? = nil,
        launchWorkspace: PublishLaunchWorkspace? = nil,
        actionItems: [PublishActionItem] = [],
        continuity: PublishContinuity? = nil,
        updatedAt: String = ""
    ) {
        self.projects = projects
        self.revenueSummary = revenueSummary
        self.upcoming = upcoming
        self.pendingReviews = pendingReviews
        self.pendingReviewsCount = pendingReviewsCount
        self.launchControl = launchControl
        self.launchWorkspace = launchWorkspace
        self.actionItems = actionItems
        self.continuity = continuity
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
        launchWorkspace = try container.decodeIfPresent(PublishLaunchWorkspace.self, forKey: .launchWorkspace)
        actionItems = try container.decodeIfPresent([PublishActionItem].self, forKey: .actionItems) ?? []
        continuity = try container.decodeIfPresent(PublishContinuity.self, forKey: .continuity)
        updatedAt = try container.decodeIfPresent(String.self, forKey: .updatedAt) ?? ""
    }
}

public struct PublishContinuity: Codable, Sendable {
    public let subjectDisplayName: String
    public let briefingStyle: String
    public let launchFocus: String
    public let activePlatforms: [String]
    public let pendingReviewPressure: Int
    public let profileFactCount: Int
    public let guidanceLines: [String]
    public let recentProfileFacts: [PublishContinuityFact]
    public let recentFirstLight: [PublishContinuityMoment]

    enum CodingKeys: String, CodingKey {
        case subjectDisplayName = "subject_display_name"
        case briefingStyle = "briefing_style"
        case launchFocus = "launch_focus"
        case activePlatforms = "active_platforms"
        case pendingReviewPressure = "pending_review_pressure"
        case profileFactCount = "profile_fact_count"
        case guidanceLines = "guidance_lines"
        case recentProfileFacts = "recent_profile_facts"
        case recentFirstLight = "recent_first_light"
    }
}

public struct PublishContinuityFact: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let summary: String
}

public struct PublishContinuityMoment: Codable, Sendable, Identifiable {
    public let id: String
    public let label: String
    public let summary: String
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
    public let checklistProgress: String
    public let checklistPercent: Int
    public let platformFocus: String
    public let updatedAt: String

    public var id: String { projectId }

    enum CodingKeys: String, CodingKey {
        case projectId = "project_id"
        case title, type, status, platform, url, description, notes
        case checklistProgress = "checklist_progress"
        case checklistPercent = "checklist_percent"
        case platformFocus = "platform_focus"
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
        checklistProgress: String = "",
        checklistPercent: Int = 0,
        platformFocus: String = "",
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
        self.checklistProgress = checklistProgress
        self.checklistPercent = checklistPercent
        self.platformFocus = platformFocus
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
        checklistProgress = try container.decodeIfPresent(String.self, forKey: .checklistProgress) ?? ""
        checklistPercent = try container.decodeIfPresent(Int.self, forKey: .checklistPercent) ?? 0
        platformFocus = try container.decodeIfPresent(String.self, forKey: .platformFocus) ?? ""
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

public struct PublishLaunchWorkspace: Codable, Sendable {
    public let projectId: String
    public let title: String
    public let platform: String
    public let platformFocus: String
    public let checklistProgress: String
    public let checklistPercent: Int
    public let nextChecklistStep: String
    public let launchSlug: String
    public let assetStatus: String
    public let generatedAt: String
    public let checklist: [PublishChecklistItem]
    public let assets: [PublishAssetSummary]

    enum CodingKeys: String, CodingKey {
        case projectId = "project_id"
        case title, platform
        case platformFocus = "platform_focus"
        case checklistProgress = "checklist_progress"
        case checklistPercent = "checklist_percent"
        case nextChecklistStep = "next_checklist_step"
        case launchSlug = "launch_slug"
        case assetStatus = "asset_status"
        case generatedAt = "generated_at"
        case checklist, assets
    }
}

public struct PublishChecklistItem: Codable, Identifiable, Sendable {
    public let step: String
    public let label: String
    public let order: Int
    public let completed: Bool
    public let completedAt: String

    public var id: String { step }

    enum CodingKeys: String, CodingKey {
        case step, label, order, completed
        case completedAt = "completed_at"
    }
}

public struct PublishAssetSummary: Codable, Identifiable, Sendable {
    public let key: String
    public let title: String
    public let status: String
    public let itemCount: Int
    public let detail: String

    public var id: String { key }

    enum CodingKeys: String, CodingKey {
        case key, title, status, detail
        case itemCount = "item_count"
    }
}

public struct PublishReviewActionResult: Codable, Sendable {
    public let requestId: String
    public let status: String
    public let review: PublishReview
    public let performedAction: String?
    public let boundaryDecision: String?
    public let boundaryReason: String?
    public let trustZone: String?
    public let authorityStage: String?
    public let arenaStatus: String?
    public let approvalMode: String?
    public let feedback: String?

    enum CodingKeys: String, CodingKey {
        case status, review, feedback
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

public struct PublishChecklistActionResult: Codable, Sendable {
    public let status: String
    public let projectId: String
    public let step: String
    public let label: String
    public let completed: Bool
    public let progress: String
    public let percent: Int
    public let workspace: PublishLaunchWorkspace?
    public let focus: PublishProgressFocus?

    enum CodingKeys: String, CodingKey {
        case status, step, label, completed, progress, percent, workspace, focus
        case projectId = "project_id"
    }
}

public struct PublishProgressFocus: Codable, Sendable {
    public let module: String
    public let reason: String
    public let route: String
    public let savedAt: String

    enum CodingKeys: String, CodingKey {
        case module, reason, route
        case savedAt = "saved_at"
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
    public let runtime: HuddleRuntimeSummary?
    public let partyMode: HuddlePartyStatus?
    public let dossiers: [HuddleDossierSummary]
    public let ideaInbox: HuddleIdeaInbox
    public let continuity: HuddleContinuity?
    public let updatedAt:  String

    enum CodingKeys: String, CodingKey {
        case reports, blockers, highlights, approvals
        case approvalsCount = "approvals_count"
        case totalActiveWork = "total_active_work"
        case runtime
        case partyMode = "party_mode"
        case dossiers
        case ideaInbox = "idea_inbox"
        case continuity
        case updatedAt = "updated_at"
    }

    public init(
        reports: [AgentReport] = [],
        blockers: [String] = [],
        highlights: [String] = [],
        approvals: [HuddleApproval] = [],
        approvalsCount: Int = 0,
        totalActiveWork: Int = 0,
        runtime: HuddleRuntimeSummary? = nil,
        partyMode: HuddlePartyStatus? = nil,
        dossiers: [HuddleDossierSummary] = [],
        ideaInbox: HuddleIdeaInbox = HuddleIdeaInbox(),
        continuity: HuddleContinuity? = nil,
        updatedAt: String = ""
    ) {
        self.reports = reports
        self.blockers = blockers
        self.highlights = highlights
        self.approvals = approvals
        self.approvalsCount = approvalsCount
        self.totalActiveWork = totalActiveWork
        self.runtime = runtime
        self.partyMode = partyMode
        self.dossiers = dossiers
        self.ideaInbox = ideaInbox
        self.continuity = continuity
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
        runtime = try container.decodeIfPresent(HuddleRuntimeSummary.self, forKey: .runtime)
        partyMode = try container.decodeIfPresent(HuddlePartyStatus.self, forKey: .partyMode)
        dossiers = try container.decodeIfPresent([HuddleDossierSummary].self, forKey: .dossiers) ?? []
        ideaInbox = try container.decodeIfPresent(HuddleIdeaInbox.self, forKey: .ideaInbox) ?? HuddleIdeaInbox()
        continuity = try container.decodeIfPresent(HuddleContinuity.self, forKey: .continuity)
        updatedAt = try container.decodeIfPresent(String.self, forKey: .updatedAt) ?? ""
    }
}

public struct HuddleIdeaInbox: Codable, Sendable {
    public let total: Int
    public let capturedCount: Int
    public let queuedCount: Int
    public let recent: [HuddleIdeaSummary]

    enum CodingKeys: String, CodingKey {
        case total
        case capturedCount = "captured_count"
        case queuedCount = "queued_count"
        case recent
    }

    public init(
        total: Int = 0,
        capturedCount: Int = 0,
        queuedCount: Int = 0,
        recent: [HuddleIdeaSummary] = []
    ) {
        self.total = total
        self.capturedCount = capturedCount
        self.queuedCount = queuedCount
        self.recent = recent
    }
}

public struct HuddleIdeaSummary: Codable, Identifiable, Sendable {
    public let id: String
    public let text: String
    public let status: String
    public let domain: String
    public let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, text, status, domain
        case createdAt = "created_at"
    }
}

public struct HuddleContinuity: Codable, Sendable {
    public let subjectDisplayName: String
    public let councilFocus: String
    public let activeDomains: [String]
    public let readyDossierCount: Int
    public let profileFactCount: Int
    public let guidanceLines: [String]
    public let recentProfileFacts: [HuddleContinuityFact]
    public let recentFirstLight: [HuddleContinuityMoment]

    enum CodingKeys: String, CodingKey {
        case subjectDisplayName = "subject_display_name"
        case councilFocus = "council_focus"
        case activeDomains = "active_domains"
        case readyDossierCount = "ready_dossier_count"
        case profileFactCount = "profile_fact_count"
        case guidanceLines = "guidance_lines"
        case recentProfileFacts = "recent_profile_facts"
        case recentFirstLight = "recent_first_light"
    }
}

public struct HuddleContinuityFact: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let summary: String
}

public struct HuddleContinuityMoment: Codable, Sendable, Identifiable {
    public let id: String
    public let label: String
    public let summary: String
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

public struct HuddleRuntimeSummary: Codable, Sendable {
    public let activeMode: String
    public let quietHoursActive: Bool
    public let awakeCount: Int
    public let idleCount: Int
    public let blockedCount: Int
    public let lastTickAt: String
    public let statuses: [HuddleRuntimeAgent]

    enum CodingKeys: String, CodingKey {
        case activeMode = "active_mode"
        case quietHoursActive = "quiet_hours_active"
        case awakeCount = "awake_count"
        case idleCount = "idle_count"
        case blockedCount = "blocked_count"
        case lastTickAt = "last_tick_at"
        case statuses
    }
}

public struct HuddleRuntimeAgent: Codable, Identifiable, Sendable {
    public let agentId: String
    public let label: String
    public let state: String
    public let reason: String
    public let lastRunAt: String
    public let nextRunAt: String
    public let dueNow: Bool
    public let priority: Int

    public var id: String { agentId }

    enum CodingKeys: String, CodingKey {
        case agentId = "agent_id"
        case label, state, reason, priority
        case lastRunAt = "last_run_at"
        case nextRunAt = "next_run_at"
        case dueNow = "due_now"
    }
}

public struct HuddlePartyStatus: Codable, Sendable {
    public let status: String
    public let triggeredBy: String
    public let dossiersBuiltCount: Int
    public let dossiersAttempted: Int
    public let itemsDreamed: Int
    public let itemsResearched: Int
    public let lastLog: String
    public let startedAt: String
    public let endedAt: String

    enum CodingKeys: String, CodingKey {
        case status
        case triggeredBy = "triggered_by"
        case dossiersBuiltCount = "dossiers_built_count"
        case dossiersAttempted = "dossiers_attempted"
        case itemsDreamed = "items_dreamed"
        case itemsResearched = "items_researched"
        case lastLog = "last_log"
        case startedAt = "started_at"
        case endedAt = "ended_at"
    }
}

public struct HuddlePartyModeActionResult: Codable, Sendable {
    public let requestId: String
    public let status: String
    public let performedAction: String?
    public let boundaryDecision: String?
    public let boundaryReason: String?
    public let trustZone: String?
    public let authorityStage: String?
    public let arenaStatus: String?
    public let approvalMode: String?
    public let focus: HuddleProgressFocus?

    enum CodingKeys: String, CodingKey {
        case status
        case requestId = "request_id"
        case performedAction = "performed_action"
        case boundaryDecision = "boundary_decision"
        case boundaryReason = "boundary_reason"
        case trustZone = "trust_zone"
        case authorityStage = "authority_stage"
        case arenaStatus = "arena_status"
        case approvalMode = "approval_mode"
        case focus
    }
}

public struct HuddleApprovalActionResult: Codable, Sendable {
    public let status: String
    public let workId: String
    public let title: String
    public let focus: HuddleProgressFocus?

    enum CodingKeys: String, CodingKey {
        case status
        case workId = "work_id"
        case title
        case focus
    }
}

public struct HuddleIdeaActionResult: Codable, Sendable {
    public let status: String
    public let idea: HuddleIdeaSummary?
    public let focus: HuddleProgressFocus?
}

public struct HuddleIdeaResearchActionResult: Codable, Sendable {
    public let status: String?
    public let queued: Bool?
    public let workId: String?
    public let message: String?
    public let idea: HuddleIdeaSummary?
    public let focus: HuddleProgressFocus?

    enum CodingKeys: String, CodingKey {
        case status, queued, message, idea, focus
        case workId = "work_id"
    }
}

public struct HuddleProgressFocus: Codable, Equatable, Sendable {
    public let module: String
    public let reason: String
    public let route: String
    public let savedAt: String

    enum CodingKeys: String, CodingKey {
        case module
        case reason
        case route
        case savedAt = "saved_at"
    }
}

public struct HuddleDossierSummary: Codable, Identifiable, Sendable {
    public let dossierId: String
    public let title: String
    public let status: String
    public let executiveSummary: String
    public let firstAction: String
    public let confidenceScore: Double
    public let revenueEstimateLow: Int
    public let revenueEstimateHigh: Int
    public let effortHours: Int
    public let updatedAt: String

    public var id: String { dossierId }

    enum CodingKeys: String, CodingKey {
        case dossierId = "dossier_id"
        case title, status
        case executiveSummary = "executive_summary"
        case firstAction = "first_action"
        case confidenceScore = "confidence_score"
        case revenueEstimateLow = "revenue_estimate_low"
        case revenueEstimateHigh = "revenue_estimate_high"
        case effortHours = "effort_hours"
        case updatedAt = "updated_at"
    }
}
