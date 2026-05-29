import Foundation

// MARK: - BriefingPacket

/// Full 5-zone Chamber home-screen packet returned by GET /api/apple/briefing
public struct BriefingPacket: Codable, Sendable {
    public let briefingItems: [BriefingItem]
    public let workingItems: [WorkingItem]
    public let needsItems: [NeedsItem]
    public let driftItems: [DriftItem]
    public let greeting: String
    public let mode: String
    public let generatedAt: String

    public init(
        briefingItems: [BriefingItem],
        workingItems: [WorkingItem],
        needsItems: [NeedsItem],
        driftItems: [DriftItem],
        greeting: String,
        mode: String,
        generatedAt: String
    ) {
        self.briefingItems = briefingItems
        self.workingItems = workingItems
        self.needsItems = needsItems
        self.driftItems = driftItems
        self.greeting = greeting
        self.mode = mode
        self.generatedAt = generatedAt
    }

    enum CodingKeys: String, CodingKey {
        case briefingItems = "briefing_items"
        case workingItems = "working_items"
        case needsItems = "needs_items"
        case driftItems = "drift_items"
        case greeting
        case mode
        case generatedAt = "generated_at"
    }
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
        requestType: String? = nil
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
    }

    enum CodingKeys: String, CodingKey {
        case id, text, detail, agent, risk, status
        case expiresIn = "expires_in"
        case createdAt = "created_at"
        case allowedActions = "allowed_actions"
        case requestType = "request_type"
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
