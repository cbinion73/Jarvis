import Foundation

// MARK: - SpeakResponse

/// Response envelope returned by POST /api/apple/speak
public struct SpeakResponse: Codable, Sendable {
    public let response: String
    public let agent: String
    /// Whether the response should be spoken aloud by TTS on the device
    public let speak: Bool

    public init(response: String, agent: String, speak: Bool) {
        self.response = response
        self.agent = agent
        self.speak = speak
    }
}

// MARK: - ApprovalResponse

/// Returned by POST /api/apple/home/command and POST /api/apple/approvals/{id}/approve
public struct ApprovalResponse: Codable, Sendable {
    public let requestId: String
    /// "pending_approval" | "approved" | "rejected"
    public let status: String

    public init(requestId: String, status: String) {
        self.requestId = requestId
        self.status = status
    }

    enum CodingKeys: String, CodingKey {
        case requestId = "request_id"
        case status
    }
}

// MARK: - VoiceGreeting

/// Returned by GET /api/apple/voice/greeting
public struct VoiceGreeting: Codable, Sendable {
    public let greeting: String
    /// "morning" | "afternoon" | "evening" | "night"
    public let mode: String

    public init(greeting: String, mode: String) {
        self.greeting = greeting
        self.mode = mode
    }
}
