import Foundation

// MARK: - CatalystOverview

/// Lightweight Catalyst workspace overview returned by GET /api/apple/catalyst
public struct CatalystOverview: Codable, Sendable {
    public let activeWork:  [WorkLifecycleItem]
    public let signals:     [CatalystSignal]
    public let portfolio:   [String: Int]
    public let updatedAt:   String

    enum CodingKeys: String, CodingKey {
        case activeWork  = "active_work"
        case signals
        case portfolio
        case updatedAt   = "updated_at"
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
