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
