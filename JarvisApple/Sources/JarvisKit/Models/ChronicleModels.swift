import Foundation

// MARK: - ChronicleOverview

/// Recent Chronicle entries and supporting context returned by GET /api/apple/chronicle
public struct ChronicleOverview: Codable, Sendable {
    public let entries: [ChronicleEntry]
    public let context: ChronicleContext?
    public let patterns: ChroniclePatterns?
    public let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case entries, context, patterns
        case updatedAt = "updated_at"
    }

    public init(
        entries: [ChronicleEntry] = [],
        context: ChronicleContext? = nil,
        patterns: ChroniclePatterns? = nil,
        updatedAt: String = ""
    ) {
        self.entries = entries
        self.context = context
        self.patterns = patterns
        self.updatedAt = updatedAt
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        entries = try container.decodeIfPresent([ChronicleEntry].self, forKey: .entries) ?? []
        context = try container.decodeIfPresent(ChronicleContext.self, forKey: .context)
        patterns = try container.decodeIfPresent(ChroniclePatterns.self, forKey: .patterns)
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

// MARK: - FaithOverview

/// Daily word and morning spiritual context returned by GET /api/apple/faith
public struct FaithOverview: Codable, Sendable {
    public let dailyWord: DailyWord
    public let morningContext: [String: String]
    public let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case dailyWord = "daily_word"
        case morningContext = "morning_context"
        case updatedAt = "updated_at"
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
