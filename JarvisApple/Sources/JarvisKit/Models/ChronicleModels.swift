import Foundation

// MARK: - ChronicleOverview

/// Recent Chronicle entries and supporting context returned by GET /api/apple/chronicle
public struct ChronicleOverview: Codable, Sendable {
    public let entries: [ChronicleEntry]
    public let context: ChronicleContext?
    public let patterns: ChroniclePatterns?
    public let continuity: ChronicleContinuity?
    public let studyWorkspace: ChronicleStudyWorkspace?
    public let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case entries, context, patterns, continuity
        case studyWorkspace = "study_workspace"
        case updatedAt = "updated_at"
    }

    public init(
        entries: [ChronicleEntry] = [],
        context: ChronicleContext? = nil,
        patterns: ChroniclePatterns? = nil,
        continuity: ChronicleContinuity? = nil,
        studyWorkspace: ChronicleStudyWorkspace? = nil,
        updatedAt: String = ""
    ) {
        self.entries = entries
        self.context = context
        self.patterns = patterns
        self.continuity = continuity
        self.studyWorkspace = studyWorkspace
        self.updatedAt = updatedAt
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        entries = try container.decodeIfPresent([ChronicleEntry].self, forKey: .entries) ?? []
        context = try container.decodeIfPresent(ChronicleContext.self, forKey: .context)
        patterns = try container.decodeIfPresent(ChroniclePatterns.self, forKey: .patterns)
        continuity = try container.decodeIfPresent(ChronicleContinuity.self, forKey: .continuity)
        studyWorkspace = try container.decodeIfPresent(ChronicleStudyWorkspace.self, forKey: .studyWorkspace)
        updatedAt = try container.decodeIfPresent(String.self, forKey: .updatedAt) ?? ""
    }
}

// MARK: - ChronicleEntry

public struct ChronicleEntry: Codable, Identifiable, Sendable {
    public let id: String
    public let type: String
    public let title: String
    public let body: String
    public let scripture: String?
    public let timestamp: String
}

public struct ChronicleContext: Codable, Sendable {
    public let study: ChronicleStudy?
    public let activePrayers: [ChroniclePrayer]
    public let todaysRhythm: ChronicleRhythm?
    public let topThemes: [String]
    public let totalEntries: Int
    public let activePrayerCount: Int
    public let answeredPrayerCount: Int

    enum CodingKeys: String, CodingKey {
        case study
        case activePrayers = "active_prayers"
        case todaysRhythm = "todays_rhythm"
        case topThemes = "top_themes"
        case totalEntries = "total_entries"
        case activePrayerCount = "active_prayer_count"
        case answeredPrayerCount = "answered_prayer_count"
    }

    public init(
        study: ChronicleStudy? = nil,
        activePrayers: [ChroniclePrayer] = [],
        todaysRhythm: ChronicleRhythm? = nil,
        topThemes: [String] = [],
        totalEntries: Int = 0,
        activePrayerCount: Int = 0,
        answeredPrayerCount: Int = 0
    ) {
        self.study = study
        self.activePrayers = activePrayers
        self.todaysRhythm = todaysRhythm
        self.topThemes = topThemes
        self.totalEntries = totalEntries
        self.activePrayerCount = activePrayerCount
        self.answeredPrayerCount = answeredPrayerCount
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        study = try container.decodeIfPresent(ChronicleStudy.self, forKey: .study)
        activePrayers = try container.decodeIfPresent([ChroniclePrayer].self, forKey: .activePrayers) ?? []
        todaysRhythm = try container.decodeIfPresent(ChronicleRhythm.self, forKey: .todaysRhythm)
        topThemes = try container.decodeIfPresent([String].self, forKey: .topThemes) ?? []
        totalEntries = try container.decodeIfPresent(Int.self, forKey: .totalEntries) ?? 0
        activePrayerCount = try container.decodeIfPresent(Int.self, forKey: .activePrayerCount) ?? 0
        answeredPrayerCount = try container.decodeIfPresent(Int.self, forKey: .answeredPrayerCount) ?? 0
    }
}

public struct ChronicleStudy: Codable, Sendable {
    public let passage: String
    public let title: String
    public let date: String
}

public struct ChroniclePrayer: Codable, Identifiable, Sendable {
    public let id: String
    public let text: String
    public let category: String
    public let timesPrayed: Int
    public let lastPrayedAt: String
    public let answered: Bool
    public let answerSummary: String?

    enum CodingKeys: String, CodingKey {
        case id, text, category, answered
        case timesPrayed = "times_prayed"
        case lastPrayedAt = "last_prayed_at"
        case answerSummary = "answer_summary"
    }
}

public struct ChronicleRhythm: Codable, Sendable {
    public let name: String
    public let description: String
}

public struct ChroniclePatterns: Codable, Sendable {
    public let windowDays: Int
    public let totalRecentEntries: Int
    public let entryTypeBreakdown: [String: Int]
    public let recurringThemes: [ChronicleThemeCount]
    public let prayerArc: ChroniclePrayerArc
    public let writingStreakDays: Int

    enum CodingKeys: String, CodingKey {
        case windowDays = "window_days"
        case totalRecentEntries = "total_recent_entries"
        case entryTypeBreakdown = "entry_type_breakdown"
        case recurringThemes = "recurring_themes"
        case prayerArc = "prayer_arc"
        case writingStreakDays = "writing_streak_days"
    }

    public init(
        windowDays: Int = 30,
        totalRecentEntries: Int = 0,
        entryTypeBreakdown: [String: Int] = [:],
        recurringThemes: [ChronicleThemeCount] = [],
        prayerArc: ChroniclePrayerArc = ChroniclePrayerArc(),
        writingStreakDays: Int = 0
    ) {
        self.windowDays = windowDays
        self.totalRecentEntries = totalRecentEntries
        self.entryTypeBreakdown = entryTypeBreakdown
        self.recurringThemes = recurringThemes
        self.prayerArc = prayerArc
        self.writingStreakDays = writingStreakDays
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        windowDays = try container.decodeIfPresent(Int.self, forKey: .windowDays) ?? 30
        totalRecentEntries = try container.decodeIfPresent(Int.self, forKey: .totalRecentEntries) ?? 0
        entryTypeBreakdown = try container.decodeIfPresent([String: Int].self, forKey: .entryTypeBreakdown) ?? [:]
        recurringThemes = try container.decodeIfPresent([ChronicleThemeCount].self, forKey: .recurringThemes) ?? []
        prayerArc = try container.decodeIfPresent(ChroniclePrayerArc.self, forKey: .prayerArc) ?? ChroniclePrayerArc()
        writingStreakDays = try container.decodeIfPresent(Int.self, forKey: .writingStreakDays) ?? 0
    }
}

public struct ChronicleThemeCount: Codable, Identifiable, Sendable {
    public var id: String { theme }
    public let theme: String
    public let count: Int

    public init(theme: String, count: Int) {
        self.theme = theme
        self.count = count
    }
}

public struct ChroniclePrayerArc: Codable, Sendable {
    public let totalActive: Int
    public let answeredTotal: Int
    public let answeredRecent: Int

    enum CodingKeys: String, CodingKey {
        case totalActive = "total_active"
        case answeredTotal = "answered_total"
        case answeredRecent = "answered_recent"
    }

    public init(
        totalActive: Int = 0,
        answeredTotal: Int = 0,
        answeredRecent: Int = 0
    ) {
        self.totalActive = totalActive
        self.answeredTotal = answeredTotal
        self.answeredRecent = answeredRecent
    }
}

public struct ChronicleStudyWorkspace: Codable, Sendable {
    public let passage: String
    public let title: String
    public let date: String
    public let focusSummary: String
    public let prompts: [String]

    enum CodingKeys: String, CodingKey {
        case passage, title, date, prompts
        case focusSummary = "focus_summary"
    }
}

public struct ChronicleContinuity: Codable, Sendable {
    public let relevantFacts: [ChronicleContinuityFact]
    public let similarEntries: [ChronicleEntry]
    public let situations: [ChronicleContinuitySituation]
    public let recallPrompt: String

    enum CodingKeys: String, CodingKey {
        case relevantFacts = "relevant_facts"
        case similarEntries = "similar_entries"
        case situations
        case recallPrompt = "recall_prompt"
    }
}

public struct ChronicleContinuityFact: Codable, Identifiable, Sendable {
    public let factId: String
    public let title: String
    public let summary: String
    public let lane: String
    public let updatedAt: String
    public let tags: [String]

    public var id: String { factId }

    enum CodingKeys: String, CodingKey {
        case title, summary, lane, tags
        case factId = "fact_id"
        case updatedAt = "updated_at"
    }
}

public struct ChronicleContinuitySituation: Codable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let summary: String
    public let signals: [String]
    public let matchedFactCount: Int

    enum CodingKeys: String, CodingKey {
        case id, label, summary, signals
        case matchedFactCount = "matched_fact_count"
    }
}

// MARK: - FaithOverview

/// Daily word and morning spiritual context returned by GET /api/apple/faith
public struct FaithOverview: Codable, Sendable {
    public let dailyWord: DailyWord
    public let morningContext: [String: String]
    public let agents: [FaithAgentSummary]
    public let formationPrompts: [String]
    public let continuity: FaithContinuity?
    public let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case dailyWord = "daily_word"
        case morningContext = "morning_context"
        case agents
        case formationPrompts = "formation_prompts"
        case continuity
        case updatedAt = "updated_at"
    }
}

public struct FaithContinuity: Codable, Sendable {
    public let subjectDisplayName: String
    public let theme: String
    public let focus: String
    public let passage: String
    public let councilDomains: [String]
    public let guidanceLines: [String]
    public let profileFactCount: Int
    public let recentProfileFacts: [FaithContinuityFact]
    public let recentFirstLight: [FaithContinuityMoment]

    enum CodingKeys: String, CodingKey {
        case subjectDisplayName = "subject_display_name"
        case theme, focus, passage
        case councilDomains = "council_domains"
        case guidanceLines = "guidance_lines"
        case profileFactCount = "profile_fact_count"
        case recentProfileFacts = "recent_profile_facts"
        case recentFirstLight = "recent_first_light"
    }
}

public struct FaithContinuityFact: Codable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let summary: String
}

public struct FaithContinuityMoment: Codable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let summary: String
}

public struct FaithAgentSummary: Codable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let title: String
    public let domain: String
    public let color: String
    public let initials: String
    public let description: String
}

public struct FaithChatMessage: Codable, Identifiable, Sendable {
    public let id: String
    public let role: String
    public let content: String

    public init(id: String = UUID().uuidString, role: String, content: String) {
        self.id = id
        self.role = role
        self.content = content
    }
}

public struct FaithChatPayload: Encodable, Sendable {
    public let agentId: String
    public let passage: String
    public let messages: [FaithChatMessage]

    public init(agentId: String, passage: String = "", messages: [FaithChatMessage]) {
        self.agentId = agentId
        self.passage = passage
        self.messages = messages
    }

    enum CodingKeys: String, CodingKey {
        case agentId = "agent_id"
        case passage
        case messages
    }
}

public struct FaithChatResponse: Decodable, Sendable {
    public let reply: String
    public let agentId: String
    public let agentName: String

    enum CodingKeys: String, CodingKey {
        case reply
        case agentId = "agent_id"
        case agentName = "agent_name"
    }
}

// MARK: - DailyWord

public struct DailyWord: Codable, Sendable {
    public let agent: String
    public let agentTitle: String
    public let word: String
    public let passage: String
    public let domain: String
    public let generatedAt: String

    enum CodingKeys: String, CodingKey {
        case agent
        case agentTitle = "agent_title"
        case word, passage, domain
        case generatedAt = "generated_at"
    }
}

// MARK: - ChronicleCapture

public struct ChronicleCapture: Codable, Sendable {
    public let type: String
    public let note: String
    public let actorId: String

    public init(type: String, note: String, actorId: String = "chris") {
        self.type = type
        self.note = note
        self.actorId = actorId
    }

    enum CodingKeys: String, CodingKey {
        case type, note
        case actorId = "actor_id"
    }
}

public struct ChroniclePrayerActionPayload: Codable, Sendable {
    public let actorId: String
    public let note: String

    public init(actorId: String = "chris", note: String = "") {
        self.actorId = actorId
        self.note = note
    }

    enum CodingKeys: String, CodingKey {
        case note
        case actorId = "actor_id"
    }
}

public struct ChroniclePrayerActionResult: Codable, Sendable {
    public let status: String
    public let prayerId: String
    public let timesPrayed: Int?
    public let lastPrayedAt: String?
    public let answeredAt: String?

    enum CodingKeys: String, CodingKey {
        case status
        case prayerId = "prayer_id"
        case timesPrayed = "times_prayed"
        case lastPrayedAt = "last_prayed_at"
        case answeredAt = "answered_at"
    }
}

public struct ChronicleStudySavePayload: Codable, Sendable {
    public let actorId: String
    public let title: String
    public let passage: String
    public let notes: String

    public init(actorId: String = "chris", title: String, passage: String, notes: String) {
        self.actorId = actorId
        self.title = title
        self.passage = passage
        self.notes = notes
    }

    enum CodingKeys: String, CodingKey {
        case title, passage, notes
        case actorId = "actor_id"
    }
}

public struct ChronicleStudySaveResult: Codable, Sendable {
    public let captured: Bool
    public let entryId: String

    enum CodingKeys: String, CodingKey {
        case captured
        case entryId = "entry_id"
    }
}
