import Foundation

// MARK: - BriefingPacket

/// Full 5-zone Chamber home-screen packet returned by GET /api/apple/briefing
public struct BriefingPacket: Codable, Sendable {
    public let commandItems: [CommandItem]
    public let briefingItems: [BriefingItem]
    public let workingItems: [WorkingItem]
    public let needsItems: [NeedsItem]
    public let driftItems: [DriftItem]
    public let continuity: BriefingContinuity?
    public let whileYouWereAway: WhileYouWereAwayReport?
    public let greeting: String
    public let mode: String
    public let generatedAt: String

    public init(
        commandItems: [CommandItem] = [],
        briefingItems: [BriefingItem],
        workingItems: [WorkingItem],
        needsItems: [NeedsItem],
        driftItems: [DriftItem],
        continuity: BriefingContinuity? = nil,
        whileYouWereAway: WhileYouWereAwayReport? = nil,
        greeting: String,
        mode: String,
        generatedAt: String
    ) {
        self.commandItems = commandItems
        self.briefingItems = briefingItems
        self.workingItems = workingItems
        self.needsItems = needsItems
        self.driftItems = driftItems
        self.continuity = continuity
        self.whileYouWereAway = whileYouWereAway
        self.greeting = greeting
        self.mode = mode
        self.generatedAt = generatedAt
    }

    enum CodingKeys: String, CodingKey {
        case commandItems = "command_items"
        case briefingItems = "briefing_items"
        case workingItems = "working_items"
        case needsItems = "needs_items"
        case driftItems = "drift_items"
        case continuity
        case whileYouWereAway = "while_you_were_away"
        case greeting
        case mode
        case generatedAt = "generated_at"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        commandItems = try container.decodeIfPresent([CommandItem].self, forKey: .commandItems) ?? []
        briefingItems = try container.decode([BriefingItem].self, forKey: .briefingItems)
        workingItems = try container.decode([WorkingItem].self, forKey: .workingItems)
        needsItems = try container.decode([NeedsItem].self, forKey: .needsItems)
        driftItems = try container.decode([DriftItem].self, forKey: .driftItems)
        continuity = try container.decodeIfPresent(BriefingContinuity.self, forKey: .continuity)
        whileYouWereAway = try container.decodeIfPresent(WhileYouWereAwayReport.self, forKey: .whileYouWereAway)
        greeting = try container.decode(String.self, forKey: .greeting)
        mode = try container.decode(String.self, forKey: .mode)
        generatedAt = try container.decode(String.self, forKey: .generatedAt)
    }
}

public struct BriefingContinuity: Codable, Sendable {
    public let subjectDisplayName: String
    public let preferredTone: String
    public let briefingStyle: String
    public let profileFactCount: Int
    public let pendingProposalCount: Int
    public let firstLightHistoryCount: Int
    public let guidanceLines: [String]
    public let recentProfileFacts: [BriefingContinuityFact]
    public let recentFirstLight: [BriefingContinuityMoment]
    public let longHorizonLines: [String]
    public let activeThreads: [String]

    enum CodingKeys: String, CodingKey {
        case subjectDisplayName = "subject_display_name"
        case preferredTone = "preferred_tone"
        case briefingStyle = "briefing_style"
        case profileFactCount = "profile_fact_count"
        case pendingProposalCount = "pending_proposal_count"
        case firstLightHistoryCount = "first_light_history_count"
        case guidanceLines = "guidance_lines"
        case recentProfileFacts = "recent_profile_facts"
        case recentFirstLight = "recent_first_light"
        case longHorizonLines = "long_horizon_lines"
        case activeThreads = "active_threads"
    }
}

public struct BriefingContinuityFact: Codable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let summary: String
}

public struct BriefingContinuityMoment: Codable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let summary: String
}

public struct WhileYouWereAwayReport: Codable, Sendable {
    public let headline: String
    public let summary: String
    public let windowHours: Int
    public let generatedAt: String
    public let stewardshipLanes: [WhileYouWereAwayStewardshipLane]
    public let laneReports: [WhileYouWereAwayLaneReport]
    public let quietCompletions: [WhileYouWereAwayRow]
    public let blockedWork: [WhileYouWereAwayRow]
    public let preparedWork: [WhileYouWereAwayRow]
    public let decisionCards: [WhileYouWereAwayRow]
    public let driftSignals: [WhileYouWereAwayRow]
    public let recommendation: WhileYouWereAwayRecommendation?

    enum CodingKeys: String, CodingKey {
        case headline, summary, recommendation
        case windowHours = "window_hours"
        case generatedAt = "generated_at"
        case stewardshipLanes = "stewardship_lanes"
        case laneReports = "lane_reports"
        case quietCompletions = "quiet_completions"
        case blockedWork = "blocked_work"
        case preparedWork = "prepared_work"
        case decisionCards = "decision_cards"
        case driftSignals = "drift_signals"
    }
}

public struct WhileYouWereAwayStewardshipLane: Codable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let summary: String
    public let reportSummaries: [WhileYouWereAwayRow]
    public let preparedWork: [WhileYouWereAwayRow]
    public let decisionCards: [WhileYouWereAwayRow]
    public let driftCards: [WhileYouWereAwayRow]
    public let quietCompletions: [WhileYouWereAwayRow]
    public let blockedWork: [WhileYouWereAwayRow]
    public let executionPrimitive: StewardshipLaneExecutionPrimitive?

    enum CodingKeys: String, CodingKey {
        case id, title, summary
        case reportSummaries = "report_summaries"
        case preparedWork = "prepared_work"
        case decisionCards = "decision_cards"
        case driftCards = "drift_cards"
        case quietCompletions = "quiet_completions"
        case blockedWork = "blocked_work"
        case executionPrimitive = "execution_primitive"
    }
}

public struct StewardshipLaneExecutionPrimitive: Codable, Sendable {
    public let packetTarget: String
    public let reviewSurface: String
    public let navigationTarget: String
    public let actionLabel: String
    public let actionDetail: String
    public let routeSummary: String
    public let laneStatus: String
    public let trustZone: String
    public let authorityStage: String
    public let arenaStatus: String
    public let approvalMode: String
    public let boundaryDecision: String
    public let boundaryReason: String

    enum CodingKeys: String, CodingKey {
        case packetTarget = "packet_target"
        case reviewSurface = "review_surface"
        case navigationTarget = "navigation_target"
        case actionLabel = "action_label"
        case actionDetail = "action_detail"
        case routeSummary = "route_summary"
        case laneStatus = "lane_status"
        case trustZone = "trust_zone"
        case authorityStage = "authority_stage"
        case arenaStatus = "arena_status"
        case approvalMode = "approval_mode"
        case boundaryDecision = "boundary_decision"
        case boundaryReason = "boundary_reason"
    }
}

public struct StewardshipLaneActionResult: Codable, Sendable {
    public let requestId: String
    public let reviewId: String
    public let status: String
    public let performedAction: String
    public let laneId: String
    public let laneTitle: String
    public let reviewSurface: String
    public let packetTarget: String
    public let boundaryDecision: String
    public let boundaryReason: String
    public let trustZone: String
    public let authorityStage: String
    public let arenaStatus: String
    public let approvalMode: String

    enum CodingKeys: String, CodingKey {
        case requestId = "request_id"
        case reviewId = "review_id"
        case status
        case performedAction = "performed_action"
        case laneId = "lane_id"
        case laneTitle = "lane_title"
        case reviewSurface = "review_surface"
        case packetTarget = "packet_target"
        case boundaryDecision = "boundary_decision"
        case boundaryReason = "boundary_reason"
        case trustZone = "trust_zone"
        case authorityStage = "authority_stage"
        case arenaStatus = "arena_status"
        case approvalMode = "approval_mode"
    }
}

public struct WhileYouWereAwayLaneReport: Codable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let summary: String
}

public struct WhileYouWereAwayRow: Codable, Identifiable, Sendable {
    public let id: String
    public let lane: String
    public let agent: String
    public let title: String
    public let summary: String
    public let timestamp: String
    public let status: String
}

public struct WhileYouWereAwayRecommendation: Codable, Sendable {
    public let title: String
    public let summary: String
    public let action: String
}

public struct CommandItem: Codable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let detail: String
    public let priority: String
    public let kind: String
}

// MARK: - BriefingItem

/// A single item in the Briefing (morning intelligence) zone
public struct BriefingItem: Codable, Identifiable, Sendable {
    public let id: String
    public let text: String
    public let sub: String?
    /// "normal" | "high"
    public let priority: String
    public let agent: String
    public let timestamp: String

    public init(
        id: String,
        text: String,
        sub: String? = nil,
        priority: String = "normal",
        agent: String,
        timestamp: String
    ) {
        self.id = id
        self.text = text
        self.sub = sub
        self.priority = priority
        self.agent = agent
        self.timestamp = timestamp
    }
}

// MARK: - WorkingItem

/// A task actively being worked on by an agent (Working zone)
public struct WorkingItem: Codable, Identifiable, Sendable {
    public let id: String
    public let agent: String
    public let action: String
    public let timestamp: String

    public init(id: String, agent: String, action: String, timestamp: String) {
        self.id = id
        self.agent = agent
        self.action = action
        self.timestamp = timestamp
    }
}

// MARK: - NeedsItem

/// A pending item requiring Sir's decision (Needs You zone)
public struct NeedsItem: Codable, Identifiable, Sendable {
    public let id: String
    public let text: String
    public let detail: String?
    public let agent: String
    /// Risk tier: "low" | "medium" | "high"
    public let risk: String
    public let expiresIn: String?
    public let createdAt: String?
    public let status: String?
    public let allowedActions: [String]
    public let requestType: String?
    public let priority: Int?
    public let tags: [String]
    public let requiresConfirmation: Bool?
    public let confirmationPhrase: String?
    public let targetSummary: String?
    public let contextLines: [String]

    public init(
        id: String,
        text: String,
        detail: String? = nil,
        agent: String,
        risk: String = "medium",
        expiresIn: String? = nil,
        createdAt: String? = nil,
        status: String? = nil,
        allowedActions: [String] = ["approve"],
        requestType: String? = nil,
        priority: Int? = nil,
        tags: [String] = [],
        requiresConfirmation: Bool? = nil,
        confirmationPhrase: String? = nil,
        targetSummary: String? = nil,
        contextLines: [String] = []
    ) {
        self.id = id
        self.text = text
        self.detail = detail
        self.agent = agent
        self.risk = risk
        self.expiresIn = expiresIn
        self.createdAt = createdAt
        self.status = status
        self.allowedActions = allowedActions
        self.requestType = requestType
        self.priority = priority
        self.tags = tags
        self.requiresConfirmation = requiresConfirmation
        self.confirmationPhrase = confirmationPhrase
        self.targetSummary = targetSummary
        self.contextLines = contextLines
    }

    enum CodingKeys: String, CodingKey {
        case id, text, detail, agent, risk, status
        case expiresIn = "expires_in"
        case createdAt = "created_at"
        case allowedActions = "allowed_actions"
        case requestType = "request_type"
        case priority, tags
        case requiresConfirmation = "requires_confirmation"
        case confirmationPhrase = "confirmation_phrase"
        case targetSummary = "target_summary"
        case contextLines = "context_lines"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        text = try container.decode(String.self, forKey: .text)
        detail = try container.decodeIfPresent(String.self, forKey: .detail)
        agent = try container.decode(String.self, forKey: .agent)
        risk = try container.decodeIfPresent(String.self, forKey: .risk) ?? "medium"
        expiresIn = try container.decodeIfPresent(String.self, forKey: .expiresIn)
        createdAt = try container.decodeIfPresent(String.self, forKey: .createdAt)
        status = try container.decodeIfPresent(String.self, forKey: .status)
        allowedActions = try container.decodeIfPresent([String].self, forKey: .allowedActions) ?? ["approve"]
        requestType = try container.decodeIfPresent(String.self, forKey: .requestType)
        priority = try container.decodeIfPresent(Int.self, forKey: .priority)
        tags = try container.decodeIfPresent([String].self, forKey: .tags) ?? []
        requiresConfirmation = try container.decodeIfPresent(Bool.self, forKey: .requiresConfirmation)
        confirmationPhrase = try container.decodeIfPresent(String.self, forKey: .confirmationPhrase)
        targetSummary = try container.decodeIfPresent(String.self, forKey: .targetSummary)
        contextLines = try container.decodeIfPresent([String].self, forKey: .contextLines) ?? []
    }
}

// MARK: - DriftItem

/// A drift signal surfaced by the Drift layer
public struct DriftItem: Codable, Identifiable, Sendable {
    public let id: String
    public let text: String
    /// "gentle" | "moderate" | "significant"
    public let severity: String
    public let agent: String

    public init(id: String, text: String, severity: String = "gentle", agent: String) {
        self.id = id
        self.text = text
        self.severity = severity
        self.agent = agent
    }
}

// MARK: - WatchStatus

/// Compact status payload for Apple Watch complications (< 200 bytes target)
public struct WatchStatus: Codable, Sendable {
    public let needsCount: Int
    public let mode: String
    public let weather: String
    public let drift: Bool
    public let ts: String

    public init(needsCount: Int, mode: String, weather: String, drift: Bool, ts: String) {
        self.needsCount = needsCount
        self.mode = mode
        self.weather = weather
        self.drift = drift
        self.ts = ts
    }

    enum CodingKeys: String, CodingKey {
        case needsCount = "needs_count"
        case mode, weather, drift, ts
    }
}
