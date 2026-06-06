import Foundation

// MARK: - SpeakResponse

/// Response envelope returned by POST /api/apple/speak
public struct SpeakResponse: Codable, Sendable {
    public let response: String
    public let agent: String
    /// Whether the response should be spoken aloud by TTS on the Apple device.
    public let speak: Bool
    /// UI-safe text for Apple surfaces to display in chat, cards, or banners.
    public let displayText: String
    /// Text the Apple client should speak aloud when `speak` is true.
    public let spokenText: String
    /// Presentation hint from JARVIS for the Apple surface.
    public let presentationMode: String
    public let conversationId: String
    public let followUpSuggestions: [String]

    public init(
        response: String,
        agent: String,
        speak: Bool,
        displayText: String? = nil,
        spokenText: String? = nil,
        presentationMode: String = "spoken_reply",
        conversationId: String = "",
        followUpSuggestions: [String] = []
    ) {
        self.response = response
        self.agent = agent
        self.speak = speak
        self.displayText = displayText ?? response
        self.spokenText = spokenText ?? response
        self.presentationMode = presentationMode
        self.conversationId = conversationId
        self.followUpSuggestions = followUpSuggestions
    }

    enum CodingKeys: String, CodingKey {
        case response
        case agent
        case speak
        case displayText = "display_text"
        case spokenText = "spoken_text"
        case presentationMode = "presentation_mode"
        case conversationId = "conversation_id"
        case followUpSuggestions = "follow_up_suggestions"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let response = try container.decode(String.self, forKey: .response)
        let agent = try container.decode(String.self, forKey: .agent)
        let speak = try container.decode(Bool.self, forKey: .speak)
        let displayText = try container.decodeIfPresent(String.self, forKey: .displayText) ?? response
        let spokenText = try container.decodeIfPresent(String.self, forKey: .spokenText) ?? response
        let presentationMode = try container.decodeIfPresent(String.self, forKey: .presentationMode) ?? "spoken_reply"
        let conversationId = try container.decodeIfPresent(String.self, forKey: .conversationId) ?? ""
        let followUpSuggestions = try container.decodeIfPresent([String].self, forKey: .followUpSuggestions) ?? []
        self.init(
            response: response,
            agent: agent,
            speak: speak,
            displayText: displayText,
            spokenText: spokenText,
            presentationMode: presentationMode,
            conversationId: conversationId,
            followUpSuggestions: followUpSuggestions
        )
    }
}

// MARK: - ApprovalResponse

/// Returned by POST /api/apple/home/command and POST /api/apple/approvals/{id}/approve
public struct ApprovalResponse: Codable, Sendable {
    public let requestId: String
    /// "pending_approval" | "approved" | "rejected"
    public let status: String
    public let boundaryDecision: String?
    public let boundaryReason: String?
    public let trustZone: String?
    public let authorityStage: String?
    public let arenaStatus: String?
    public let approvalMode: String?

    public init(
        requestId: String,
        status: String,
        boundaryDecision: String? = nil,
        boundaryReason: String? = nil,
        trustZone: String? = nil,
        authorityStage: String? = nil,
        arenaStatus: String? = nil,
        approvalMode: String? = nil
    ) {
        self.requestId = requestId
        self.status = status
        self.boundaryDecision = boundaryDecision
        self.boundaryReason = boundaryReason
        self.trustZone = trustZone
        self.authorityStage = authorityStage
        self.arenaStatus = arenaStatus
        self.approvalMode = approvalMode
    }

    enum CodingKeys: String, CodingKey {
        case requestId = "request_id"
        case status
        case boundaryDecision = "boundary_decision"
        case boundaryReason = "boundary_reason"
        case trustZone = "trust_zone"
        case authorityStage = "authority_stage"
        case arenaStatus = "arena_status"
        case approvalMode = "approval_mode"
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

public struct VoiceConsoleState: Codable, Sendable {
    public let conversation: VoiceConversationSummary
    public let recentConversations: [VoiceConversationReference]
    public let memoryOverview: VoiceMemoryOverview
    public let voiceStack: VoiceStackStatus
    public let quickCommands: [String]

    enum CodingKeys: String, CodingKey {
        case conversation
        case recentConversations = "recent_conversations"
        case memoryOverview = "memory_overview"
        case voiceStack = "voice_stack"
        case quickCommands = "quick_commands"
    }
}

public struct VoiceConversationSummary: Codable, Sendable {
    public let conversationId: String
    public let title: String
    public let updatedAt: String
    public let turnCount: Int
    public let latestUserText: String
    public let latestAssistantText: String
    public let recentTurns: [VoiceTurn]

    enum CodingKeys: String, CodingKey {
        case title
        case conversationId = "conversation_id"
        case updatedAt = "updated_at"
        case turnCount = "turn_count"
        case latestUserText = "latest_user_text"
        case latestAssistantText = "latest_assistant_text"
        case recentTurns = "recent_turns"
    }
}

public struct VoiceTurn: Codable, Sendable, Identifiable {
    public var id: String { "\(role)|\(createdAt)|\(text.prefix(24))" }
    public let role: String
    public let text: String
    public let createdAt: String
    public let agent: String

    enum CodingKeys: String, CodingKey {
        case role, text, agent
        case createdAt = "created_at"
    }
}

public struct VoiceConversationReference: Codable, Sendable, Identifiable {
    public var id: String { conversationId }
    public let conversationId: String
    public let title: String
    public let updatedAt: String
    public let turnCount: Int

    enum CodingKeys: String, CodingKey {
        case title
        case conversationId = "conversation_id"
        case updatedAt = "updated_at"
        case turnCount = "turn_count"
    }
}

public struct VoiceMemoryOverview: Codable, Sendable {
    public let profileFactCount: Int
    public let pendingProposals: Int
    public let preferredVoice: String
    public let briefingStyle: String
    public let guidanceLines: [String]
    public let recentProfileFacts: [VoiceContinuityFact]
    public let recentFirstLight: [VoiceContinuityMoment]
    public let longHorizonLines: [String]
    public let activeThreads: [String]

    enum CodingKeys: String, CodingKey {
        case profileFactCount = "profile_fact_count"
        case pendingProposals = "pending_proposals"
        case preferredVoice = "preferred_voice"
        case briefingStyle = "briefing_style"
        case guidanceLines = "guidance_lines"
        case recentProfileFacts = "recent_profile_facts"
        case recentFirstLight = "recent_first_light"
        case longHorizonLines = "long_horizon_lines"
        case activeThreads = "active_threads"
    }
}

public struct VoiceContinuityFact: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let summary: String
}

public struct VoiceContinuityMoment: Codable, Sendable, Identifiable {
    public let id: String
    public let label: String
    public let summary: String
}

public struct VoiceStackStatus: Codable, Sendable {
    public let provider: String
    public let providerLabel: String
    public let voiceLabel: String
    public let localReady: Bool
    public let cloudReady: Bool
    public let detail: String

    enum CodingKeys: String, CodingKey {
        case provider, detail
        case providerLabel = "provider_label"
        case voiceLabel = "voice_label"
        case localReady = "local_ready"
        case cloudReady = "cloud_ready"
    }
}
