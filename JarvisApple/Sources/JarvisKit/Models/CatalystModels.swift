import Foundation

// MARK: - CatalystOverview

/// Lightweight Catalyst workspace overview returned by GET /api/apple/catalyst
public struct CatalystOverview: Codable, Sendable {
    public let activeWork:  [WorkLifecycleItem]
    public let signals:     [CatalystSignal]
    public let portfolio:   CatalystPortfolio
    public let lanes: [CatalystLane]
    public let connectors: [CatalystConnector]
    public let workflowCounts: [String: Int]
    public let liveWorkspace: CatalystLiveWorkspace
    public let latestRuns: [CatalystRunSummary]
    public let continuity: CatalystContinuity
    public let updatedAt:   String

    enum CodingKeys: String, CodingKey {
        case activeWork  = "active_work"
        case signals
        case portfolio
        case lanes
        case connectors
        case workflowCounts = "workflow_counts"
        case liveWorkspace = "live_workspace"
        case latestRuns = "latest_runs"
        case continuity
        case updatedAt   = "updated_at"
    }
}

public struct CatalystContinuity: Codable, Sendable {
    public let subjectDisplayName: String
    public let briefingStyle: String
    public let activeDomains: [String]
    public let guidanceLines: [String]
    public let profileFactCount: Int
    public let hottestWorkflow: String
    public let recentProfileFacts: [CatalystContinuityFact]
    public let recentFirstLight: [CatalystContinuityMoment]

    enum CodingKeys: String, CodingKey {
        case subjectDisplayName = "subject_display_name"
        case briefingStyle = "briefing_style"
        case activeDomains = "active_domains"
        case guidanceLines = "guidance_lines"
        case profileFactCount = "profile_fact_count"
        case hottestWorkflow = "hottest_workflow"
        case recentProfileFacts = "recent_profile_facts"
        case recentFirstLight = "recent_first_light"
    }
}

public struct CatalystContinuityFact: Codable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let summary: String
}

public struct CatalystContinuityMoment: Codable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let summary: String
}

// MARK: - CatalystPortfolio

public struct CatalystPortfolio: Codable, Sendable {
    public let mission: String
    public let activeProjectTarget: Int
    public let hypothesisReviewTarget: Int
    public let lanes: [CatalystPortfolioLane]

    public var summaryCounts: [String: Int] {
        [
            "active target": activeProjectTarget,
            "hypothesis target": hypothesisReviewTarget,
            "lanes": lanes.count,
        ]
    }

    enum CodingKeys: String, CodingKey {
        case mission
        case activeProjectTarget = "active_project_target"
        case hypothesisReviewTarget = "hypothesis_review_target"
        case lanes
    }
}

public struct CatalystPortfolioLane: Codable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let status: String?
    public let projectCount: Int?

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case status
        case projectCount = "project_count"
    }
}

// MARK: - WorkLifecycleItem

public struct WorkLifecycleItem: Codable, Identifiable, Sendable {
    public let workId:  String
    public let title:   String
    public let domain:  String
    public let lane: String
    public let stage:   String
    public let updated: String

    public var id: String { workId }

    enum CodingKeys: String, CodingKey {
        case workId  = "work_id"
        case title, domain, lane, stage, updated
    }
}

// MARK: - CatalystSignal

public struct CatalystSignal: Codable, Identifiable, Sendable {
    public let signalId:  String
    public let title:     String
    public let source:    String
    public let tags:      [String]
    public let timestamp: String

    public var id: String { signalId }

    enum CodingKeys: String, CodingKey {
        case signalId  = "signal_id"
        case title, source, tags, timestamp
    }
}

public struct CatalystLane: Codable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let description: String
    public let status: String
}

public struct CatalystConnector: Codable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let status: String
    public let notes: String
}

public struct CatalystLiveWorkspace: Codable, Sendable {
    public let available: Bool
    public let live: Bool
    public let projectsCount: Int
    public let tasksCount: Int
    public let calendarCount: Int
    public let emailCount: Int
    public let retrievedAt: String

    enum CodingKeys: String, CodingKey {
        case available, live
        case projectsCount = "projects_count"
        case tasksCount = "tasks_count"
        case calendarCount = "calendar_count"
        case emailCount = "email_count"
        case retrievedAt = "retrieved_at"
    }
}

public struct CatalystRunSummary: Codable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let title: String
    public let timestamp: String
}

public struct CatalystProgressFocus: Codable, Equatable, Sendable {
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

public struct CatalystOpsFocusCandidate: Codable, Equatable, Identifiable, Sendable {
    public let module: String
    public let route: String
    public let label: String

    public var id: String { "\(module)|\(route)|\(label)" }
}

public struct CatalystApprovalEntry: Codable, Equatable, Identifiable, Sendable {
    public let requestId: String
    public let title: String
    public let agent: String
    public let risk: String
    public let detail: String
    public let relatedRoute: String

    public var id: String { requestId }

    enum CodingKeys: String, CodingKey {
        case requestId = "request_id"
        case title
        case agent
        case risk
        case detail
        case relatedRoute = "related_route"
    }
}

public struct CatalystRecoveryCaseEntry: Codable, Equatable, Identifiable, Sendable {
    public let caseId: String
    public let title: String
    public let status: String
    public let statusLabel: String
    public let detail: String
    public let executionCount: Int
    public let relatedRoute: String
    public let nextActionType: String
    public let nextActionLabel: String

    public var id: String { caseId }

    enum CodingKeys: String, CodingKey {
        case caseId = "case_id"
        case title
        case status
        case statusLabel = "status_label"
        case detail
        case executionCount = "execution_count"
        case relatedRoute = "related_route"
        case nextActionType = "next_action_type"
        case nextActionLabel = "next_action_label"
    }
}

public struct CatalystOpsActivityEntry: Codable, Equatable, Identifiable, Sendable {
    public let title: String
    public let detail: String
    public let routeLabel: String
    public let actor: String
    public let relatedRoute: String
    public let relatedKind: String

    public var id: String { "\(title)|\(detail)|\(routeLabel)|\(actor)" }

    enum CodingKeys: String, CodingKey {
        case title
        case detail
        case routeLabel = "route_label"
        case actor
        case relatedRoute = "related_route"
        case relatedKind = "related_kind"
    }
}

public struct CatalystMissionEntry: Codable, Equatable, Identifiable, Sendable {
    public let missionId: String
    public let title: String
    public let brief: String
    public let status: String
    public let lane: String
    public let nextStep: String
    public let route: String

    public var id: String { missionId }

    enum CodingKeys: String, CodingKey {
        case missionId = "mission_id"
        case title
        case brief
        case status
        case lane
        case nextStep = "next_step"
        case route
    }
}

public struct CatalystAgentOpsEntry: Codable, Equatable, Identifiable, Sendable {
    public let agentId: String
    public let name: String
    public let status: String
    public let statusClass: String
    public let assignment: String
    public let purpose: String
    public let module: String
    public let attentionReason: String
    public let lastActivity: String
    public let relatedRoute: String
    public let queueActionLabel: String

    public var id: String { agentId }

    enum CodingKeys: String, CodingKey {
        case agentId = "agent_id"
        case name
        case status
        case statusClass = "status_class"
        case assignment
        case purpose
        case module
        case attentionReason = "attention_reason"
        case lastActivity = "last_activity"
        case relatedRoute = "related_route"
        case queueActionLabel = "queue_action_label"
    }
}

public struct CatalystSupervisionEntry: Codable, Equatable, Identifiable, Sendable {
    public let requestId: String
    public let title: String
    public let agent: String
    public let risk: String
    public let detail: String
    public let actionType: String
    public let relatedRoute: String
    public let approveLabel: String
    public let rejectLabel: String

    public var id: String { requestId }

    enum CodingKeys: String, CodingKey {
        case requestId = "request_id"
        case title
        case agent
        case risk
        case detail
        case actionType = "action_type"
        case relatedRoute = "related_route"
        case approveLabel = "approve_label"
        case rejectLabel = "reject_label"
    }
}

public struct CatalystOpsCounts: Codable, Equatable, Sendable {
    public let approvalCount: Int
    public let recoveryCaseCount: Int
    public let recentActivityCount: Int
    public let focusHistoryCount: Int
    public let missionCount: Int
    public let agentOpsCount: Int
    public let supervisionCount: Int

    enum CodingKeys: String, CodingKey {
        case approvalCount = "approval_count"
        case recoveryCaseCount = "recovery_case_count"
        case recentActivityCount = "recent_activity_count"
        case focusHistoryCount = "focus_history_count"
        case missionCount = "mission_count"
        case agentOpsCount = "agent_ops_count"
        case supervisionCount = "supervision_count"
    }
}

public struct CatalystOpsOverview: Codable, Equatable, Sendable {
    public let generatedAt: String
    public let currentFocus: CatalystProgressFocus
    public let focusCandidates: [CatalystOpsFocusCandidate]
    public let approvals: [CatalystApprovalEntry]
    public let recoveryCases: [CatalystRecoveryCaseEntry]
    public let agentOps: [CatalystAgentOpsEntry]
    public let supervisionItems: [CatalystSupervisionEntry]
    public let recentActivity: [CatalystOpsActivityEntry]
    public let missions: [CatalystMissionEntry]
    public let counts: CatalystOpsCounts

    enum CodingKeys: String, CodingKey {
        case generatedAt = "generated_at"
        case currentFocus = "current_focus"
        case focusCandidates = "focus_candidates"
        case approvals
        case recoveryCases = "recovery_cases"
        case agentOps = "agent_ops"
        case supervisionItems = "supervision_items"
        case recentActivity = "recent_activity"
        case missions
        case counts
    }
}
