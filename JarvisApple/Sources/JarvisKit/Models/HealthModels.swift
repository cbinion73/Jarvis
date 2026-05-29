import Foundation

// MARK: - Apple API health models (Epic 14)

/// Daily health summary returned by GET /api/apple/health/summary
public struct HealthSummary: Codable, Sendable {
    public let stepsToday: Int
    public let heartRateAvg: Int
    public let sleepHours: Double
    public let activeCalories: Int
    public let standHours: Int
    public let hrv: Int
    /// "good" | "moderate" | "low"
    public let readiness: String
    public let thorNote: String
    public let lastSync: String
    public let dailyScore: HealthDailyScore?
    public let protocolItems: [HealthProtocolItem]
    public let alerts: [HealthAlert]
    public let nextActions: [String]

    public init(
        stepsToday: Int,
        heartRateAvg: Int,
        sleepHours: Double,
        activeCalories: Int,
        standHours: Int,
        hrv: Int,
        readiness: String,
        thorNote: String,
        lastSync: String,
        dailyScore: HealthDailyScore? = nil,
        protocolItems: [HealthProtocolItem] = [],
        alerts: [HealthAlert] = [],
        nextActions: [String] = []
    ) {
        self.stepsToday = stepsToday
        self.heartRateAvg = heartRateAvg
        self.sleepHours = sleepHours
        self.activeCalories = activeCalories
        self.standHours = standHours
        self.hrv = hrv
        self.readiness = readiness
        self.thorNote = thorNote
        self.lastSync = lastSync
        self.dailyScore = dailyScore
        self.protocolItems = protocolItems
        self.alerts = alerts
        self.nextActions = nextActions
    }

    enum CodingKeys: String, CodingKey {
        case stepsToday = "steps_today"
        case heartRateAvg = "heart_rate_avg"
        case sleepHours = "sleep_hours"
        case activeCalories = "active_calories"
        case standHours = "stand_hours"
        case hrv
        case readiness
        case thorNote = "thor_note"
        case lastSync = "last_sync"
        case dailyScore = "daily_score"
        case protocolItems = "protocol_items"
        case alerts
        case nextActions = "next_actions"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        stepsToday = try container.decode(Int.self, forKey: .stepsToday)
        heartRateAvg = try container.decode(Int.self, forKey: .heartRateAvg)
        sleepHours = try container.decode(Double.self, forKey: .sleepHours)
        activeCalories = try container.decode(Int.self, forKey: .activeCalories)
        standHours = try container.decode(Int.self, forKey: .standHours)
        hrv = try container.decode(Int.self, forKey: .hrv)
        readiness = try container.decode(String.self, forKey: .readiness)
        thorNote = try container.decode(String.self, forKey: .thorNote)
        lastSync = try container.decode(String.self, forKey: .lastSync)
        dailyScore = try container.decodeIfPresent(HealthDailyScore.self, forKey: .dailyScore)
        protocolItems = try container.decodeIfPresent([HealthProtocolItem].self, forKey: .protocolItems) ?? []
        alerts = try container.decodeIfPresent([HealthAlert].self, forKey: .alerts) ?? []
        nextActions = try container.decodeIfPresent([String].self, forKey: .nextActions) ?? []
    }
}

public struct HealthDailyScore: Codable, Sendable {
    public let value: Int
    public let grade: String
    public let message: String
    public let estimated: Bool

    public init(value: Int, grade: String, message: String, estimated: Bool = false) {
        self.value = value
        self.grade = grade
        self.message = message
        self.estimated = estimated
    }
}

public struct HealthProtocolItem: Codable, Sendable, Identifiable {
    public var id: String { "\(title)|\(detail)" }
    public let title: String
    public let detail: String
    public let emphasis: String

    public init(title: String, detail: String, emphasis: String) {
        self.title = title
        self.detail = detail
        self.emphasis = emphasis
    }
}

public struct HealthAlert: Codable, Sendable, Identifiable {
    public var id: String { "\(title)|\(detail ?? "")|\(severity)" }
    public let title: String
    public let detail: String?
    public let severity: String

    public init(title: String, detail: String? = nil, severity: String) {
        self.title = title
        self.detail = detail
        self.severity = severity
    }
}

/// A single HealthKit sample sent to POST /api/apple/health/log
public struct HealthSample: Codable, Sendable {
    /// "steps" | "heart_rate" | "sleep" | "active_calories" | "hrv" | "stand_hours"
    public let type: String
    public let value: Double
    /// ISO 8601 date or datetime string
    public let date: String
    /// "iPhone" | "AppleWatch"
    public let source: String

    public init(type: String, value: Double, date: String, source: String) {
        self.type = type
        self.value = value
        self.date = date
        self.source = source
    }
}

// MARK: - Existing health domain models

public struct HealthProfile: Codable, Equatable, Sendable {
    public var preferredUnits: [String: String]
    public var goals: [String]
    public var conditions: [String]
    public var medications: [String]
    public var consentFlags: [String: Bool]

    public init(
        preferredUnits: [String: String] = [:],
        goals: [String] = [],
        conditions: [String] = [],
        medications: [String] = [],
        consentFlags: [String: Bool] = [:]
    ) {
        self.preferredUnits = preferredUnits
        self.goals = goals
        self.conditions = conditions
        self.medications = medications
        self.consentFlags = consentFlags
    }
}

public struct HealthSignal: Codable, Equatable, Identifiable, Sendable {
    public let id: String
    public let metric: String
    public let timestamp: Date
    public let value: Double?
    public let unit: String?
    public let source: String
    public let provenance: String
    public let confidence: Double?

    public init(
        id: String,
        metric: String,
        timestamp: Date,
        value: Double?,
        unit: String?,
        source: String,
        provenance: String,
        confidence: Double?
    ) {
        self.id = id
        self.metric = metric
        self.timestamp = timestamp
        self.value = value
        self.unit = unit
        self.source = source
        self.provenance = provenance
        self.confidence = confidence
    }
}

public struct HealthTrend: Codable, Equatable, Identifiable, Sendable {
    public let id: String
    public let metric: String
    public let window: String
    public let baseline: Double?
    public let delta: Double?
    public let slope: Double?
    public let significance: String
    public let confidence: Double?

    public init(
        id: String,
        metric: String,
        window: String,
        baseline: Double?,
        delta: Double?,
        slope: Double?,
        significance: String,
        confidence: Double?
    ) {
        self.id = id
        self.metric = metric
        self.window = window
        self.baseline = baseline
        self.delta = delta
        self.slope = slope
        self.significance = significance
        self.confidence = confidence
    }
}

public struct ClinicalResult: Codable, Equatable, Identifiable, Sendable {
    public let id: String
    public let testName: String
    public let code: String?
    public let specimenDate: Date?
    public let resultText: String?
    public let numericValue: Double?
    public let unit: String?
    public let referenceRange: String?
    public let abnormalFlag: String?
    public let institution: String?
    public let provenance: String

    public init(
        id: String,
        testName: String,
        code: String? = nil,
        specimenDate: Date? = nil,
        resultText: String? = nil,
        numericValue: Double? = nil,
        unit: String? = nil,
        referenceRange: String? = nil,
        abnormalFlag: String? = nil,
        institution: String? = nil,
        provenance: String
    ) {
        self.id = id
        self.testName = testName
        self.code = code
        self.specimenDate = specimenDate
        self.resultText = resultText
        self.numericValue = numericValue
        self.unit = unit
        self.referenceRange = referenceRange
        self.abnormalFlag = abnormalFlag
        self.institution = institution
        self.provenance = provenance
    }
}

public struct HealthInsight: Codable, Equatable, Identifiable, Sendable {
    public let id: String
    public let summary: String
    public let rationale: String
    public let severity: String
    public let confidence: Double?
    public let supportingSignalIDs: [String]

    public init(
        id: String,
        summary: String,
        rationale: String,
        severity: String,
        confidence: Double? = nil,
        supportingSignalIDs: [String] = []
    ) {
        self.id = id
        self.summary = summary
        self.rationale = rationale
        self.severity = severity
        self.confidence = confidence
        self.supportingSignalIDs = supportingSignalIDs
    }
}

public struct HealthRecommendation: Codable, Equatable, Identifiable, Sendable {
    public let id: String
    public let category: String
    public let summary: String
    public let rationale: String
    public let urgency: String
    public let requiresClinicianReview: Bool
    public let supportingSignalIDs: [String]

    public init(
        id: String,
        category: String,
        summary: String,
        rationale: String,
        urgency: String,
        requiresClinicianReview: Bool,
        supportingSignalIDs: [String] = []
    ) {
        self.id = id
        self.category = category
        self.summary = summary
        self.rationale = rationale
        self.urgency = urgency
        self.requiresClinicianReview = requiresClinicianReview
        self.supportingSignalIDs = supportingSignalIDs
    }
}

public struct EscalationEvent: Codable, Equatable, Identifiable, Sendable {
    public let id: String
    public let trigger: String
    public let escalationClass: String
    public let recommendedNextAction: String
    public let evidence: [String]

    public init(
        id: String,
        trigger: String,
        escalationClass: String,
        recommendedNextAction: String,
        evidence: [String] = []
    ) {
        self.id = id
        self.trigger = trigger
        self.escalationClass = escalationClass
        self.recommendedNextAction = recommendedNextAction
        self.evidence = evidence
    }
}
