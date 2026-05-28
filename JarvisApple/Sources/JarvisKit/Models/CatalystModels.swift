import Foundation

// MARK: - CatalystOverview

/// Lightweight Catalyst workspace overview returned by GET /api/apple/catalyst
public struct CatalystOverview: Codable, Sendable {
    public let activeWork:  [WorkLifecycleItem]
    public let signals:     [CatalystSignal]
    public let portfolio:   CatalystPortfolio
    public let updatedAt:   String

    enum CodingKeys: String, CodingKey {
        case activeWork  = "active_work"
        case signals
        case portfolio
        case updatedAt   = "updated_at"
    }
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
    public let stage:   String
    public let updated: String

    public var id: String { workId }

    enum CodingKeys: String, CodingKey {
        case workId  = "work_id"
        case title, domain, stage, updated
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
