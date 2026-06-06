import Foundation

public struct CarPlayProgressFocus: Codable, Equatable, Sendable {
    public let module: String
    public let reason: String
    public let route: String
    public let savedAt: String

    public init(module: String, reason: String, route: String, savedAt: String) {
        self.module = module
        self.reason = reason
        self.route = route
        self.savedAt = savedAt
    }

    enum CodingKeys: String, CodingKey {
        case module
        case reason
        case route
        case savedAt = "saved_at"
    }
}

public struct CarPlayOpsFocusCandidate: Codable, Equatable, Identifiable, Sendable {
    public let module: String
    public let route: String
    public let label: String

    public var id: String { "\(module)|\(route)|\(label)" }
}

public struct CarPlayApprovalEntry: Codable, Equatable, Identifiable, Sendable {
    public let requestId: String
    public let title: String
    public let agent: String
    public let risk: String
    public let actionClass: String

    public var id: String { requestId }

    enum CodingKeys: String, CodingKey {
        case requestId = "request_id"
        case title
        case agent
        case risk
        case actionClass = "action_class"
    }
}

public struct CarPlayRecoveryCaseEntry: Codable, Equatable, Identifiable, Sendable {
    public let caseId: String
    public let title: String
    public let statusLabel: String
    public let detail: String
    public let executionCount: Int
    public let relatedRoute: String

    public var id: String { caseId }

    enum CodingKeys: String, CodingKey {
        case caseId = "case_id"
        case title
        case statusLabel = "status_label"
        case detail
        case executionCount = "execution_count"
        case relatedRoute = "related_route"
    }
}

public struct CarPlayAgentOpsEntry: Codable, Equatable, Identifiable, Sendable {
    public let agentId: String
    public let name: String
    public let status: String
    public let assignment: String
    public let purpose: String
    public let attentionReason: String
    public let queueActionLabel: String

    public var id: String { agentId }

    enum CodingKeys: String, CodingKey {
        case agentId = "agent_id"
        case name
        case status
        case assignment
        case purpose
        case attentionReason = "attention_reason"
        case queueActionLabel = "queue_action_label"
    }
}

public struct CarPlaySupervisionEntry: Codable, Equatable, Identifiable, Sendable {
    public let requestId: String
    public let title: String
    public let agent: String
    public let risk: String
    public let detail: String
    public let approveLabel: String
    public let rejectLabel: String

    public var id: String { requestId }

    enum CodingKeys: String, CodingKey {
        case requestId = "request_id"
        case title
        case agent
        case risk
        case detail
        case approveLabel = "approve_label"
        case rejectLabel = "reject_label"
    }
}

public struct CarPlayHuddleSummary: Codable, Equatable, Sendable {
    public let reportsCount: Int
    public let blockersCount: Int
    public let approvalsCount: Int
    public let readyDossierCount: Int
    public let queuedIdeaCount: Int
    public let partyModeStatus: String
    public let headline: String

    enum CodingKeys: String, CodingKey {
        case reportsCount = "reports_count"
        case blockersCount = "blockers_count"
        case approvalsCount = "approvals_count"
        case readyDossierCount = "ready_dossier_count"
        case queuedIdeaCount = "queued_idea_count"
        case partyModeStatus = "party_mode_status"
        case headline
    }
}

public struct CarPlayHuddleIdeaEntry: Codable, Equatable, Identifiable, Sendable {
    public let id: String
    public let text: String
    public let status: String
    public let domain: String
    public let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, text, status, domain
        case createdAt = "created_at"
    }
}

public struct CarPlayChronicleSummary: Codable, Equatable, Sendable {
    public let latestTitle: String
    public let activePrayerCount: Int
    public let studyTitle: String
    public let reviewCount: Int
    public let headline: String

    enum CodingKeys: String, CodingKey {
        case latestTitle = "latest_title"
        case activePrayerCount = "active_prayer_count"
        case studyTitle = "study_title"
        case reviewCount = "review_count"
        case headline
    }

    public init(
        latestTitle: String = "",
        activePrayerCount: Int = 0,
        studyTitle: String = "",
        reviewCount: Int = 0,
        headline: String = ""
    ) {
        self.latestTitle = latestTitle
        self.activePrayerCount = activePrayerCount
        self.studyTitle = studyTitle
        self.reviewCount = reviewCount
        self.headline = headline
    }
}

public struct CarPlayChronicleReviewEntry: Codable, Equatable, Identifiable, Sendable {
    public let entryId: String
    public let entryTitle: String
    public let entryType: String
    public let reviewStatus: String
    public let reviewStatusLabel: String

    public var id: String { entryId }

    enum CodingKeys: String, CodingKey {
        case entryId = "entry_id"
        case entryTitle = "entry_title"
        case entryType = "entry_type"
        case reviewStatus = "review_status"
        case reviewStatusLabel = "review_status_label"
    }
}

public struct CarPlayActivityEntry: Codable, Equatable, Identifiable, Sendable {
    public let title: String
    public let detail: String
    public let routeLabel: String
    public let actor: String

    public var id: String { "\(title)|\(detail)|\(actor)|\(routeLabel)" }

    enum CodingKeys: String, CodingKey {
        case title
        case detail
        case routeLabel = "route_label"
        case actor
    }
}

public struct CarPlayMissionSummary: Codable, Equatable, Sendable {
    public let activeCount: Int
    public let pendingApprovals: Int
    public let headline: String

    enum CodingKeys: String, CodingKey {
        case activeCount = "active_count"
        case pendingApprovals = "pending_approvals"
        case headline
    }
}

public struct CarPlayAgentSummary: Codable, Equatable, Sendable {
    public let awakeCount: Int
    public let blockedCount: Int
    public let totalCount: Int

    enum CodingKeys: String, CodingKey {
        case awakeCount = "awake_count"
        case blockedCount = "blocked_count"
        case totalCount = "total_count"
    }
}

public struct CarPlayOpsCounts: Codable, Equatable, Sendable {
    public let approvalCount: Int
    public let recoveryCaseCount: Int
    public let recentActivityCount: Int
    public let recoveryActionCount: Int
    public let agentOpsCount: Int
    public let supervisionCount: Int
    public let huddleIdeaCount: Int
    public let chronicleReviewCount: Int

    enum CodingKeys: String, CodingKey {
        case approvalCount = "approval_count"
        case recoveryCaseCount = "recovery_case_count"
        case recentActivityCount = "recent_activity_count"
        case recoveryActionCount = "recovery_action_count"
        case agentOpsCount = "agent_ops_count"
        case supervisionCount = "supervision_count"
        case huddleIdeaCount = "huddle_idea_count"
        case chronicleReviewCount = "chronicle_review_count"
    }

    public init(
        approvalCount: Int = 0,
        recoveryCaseCount: Int = 0,
        recentActivityCount: Int = 0,
        recoveryActionCount: Int = 0,
        agentOpsCount: Int = 0,
        supervisionCount: Int = 0,
        huddleIdeaCount: Int = 0,
        chronicleReviewCount: Int = 0
    ) {
        self.approvalCount = approvalCount
        self.recoveryCaseCount = recoveryCaseCount
        self.recentActivityCount = recentActivityCount
        self.recoveryActionCount = recoveryActionCount
        self.agentOpsCount = agentOpsCount
        self.supervisionCount = supervisionCount
        self.huddleIdeaCount = huddleIdeaCount
        self.chronicleReviewCount = chronicleReviewCount
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        approvalCount = try container.decodeIfPresent(Int.self, forKey: .approvalCount) ?? 0
        recoveryCaseCount = try container.decodeIfPresent(Int.self, forKey: .recoveryCaseCount) ?? 0
        recentActivityCount = try container.decodeIfPresent(Int.self, forKey: .recentActivityCount) ?? 0
        recoveryActionCount = try container.decodeIfPresent(Int.self, forKey: .recoveryActionCount) ?? 0
        agentOpsCount = try container.decodeIfPresent(Int.self, forKey: .agentOpsCount) ?? 0
        supervisionCount = try container.decodeIfPresent(Int.self, forKey: .supervisionCount) ?? 0
        huddleIdeaCount = try container.decodeIfPresent(Int.self, forKey: .huddleIdeaCount) ?? 0
        chronicleReviewCount = try container.decodeIfPresent(Int.self, forKey: .chronicleReviewCount) ?? 0
    }
}

public struct CarPlayOpsOverview: Codable, Equatable, Sendable {
    public let generatedAt: String
    public let currentFocus: CarPlayProgressFocus
    public let focusCandidates: [CarPlayOpsFocusCandidate]
    public let approvals: [CarPlayApprovalEntry]
    public let recoveryCases: [CarPlayRecoveryCaseEntry]
    public let agentOps: [CarPlayAgentOpsEntry]
    public let supervisionItems: [CarPlaySupervisionEntry]
    public let huddleSummary: CarPlayHuddleSummary
    public let huddleIdeas: [CarPlayHuddleIdeaEntry]
    public let chronicleSummary: CarPlayChronicleSummary
    public let chronicleReviews: [CarPlayChronicleReviewEntry]
    public let recentActivity: [CarPlayActivityEntry]
    public let missionSummary: CarPlayMissionSummary
    public let agentSummary: CarPlayAgentSummary
    public let counts: CarPlayOpsCounts

    enum CodingKeys: String, CodingKey {
        case generatedAt = "generated_at"
        case currentFocus = "current_focus"
        case focusCandidates = "focus_candidates"
        case approvals
        case recoveryCases = "recovery_cases"
        case agentOps = "agent_ops"
        case supervisionItems = "supervision_items"
        case huddleSummary = "huddle_summary"
        case huddleIdeas = "huddle_ideas"
        case chronicleSummary = "chronicle_summary"
        case chronicleReviews = "chronicle_reviews"
        case recentActivity = "recent_activity"
        case missionSummary = "mission_summary"
        case agentSummary = "agent_summary"
        case counts
    }

    public init(
        generatedAt: String = "",
        currentFocus: CarPlayProgressFocus,
        focusCandidates: [CarPlayOpsFocusCandidate] = [],
        approvals: [CarPlayApprovalEntry] = [],
        recoveryCases: [CarPlayRecoveryCaseEntry] = [],
        agentOps: [CarPlayAgentOpsEntry] = [],
        supervisionItems: [CarPlaySupervisionEntry] = [],
        huddleSummary: CarPlayHuddleSummary,
        huddleIdeas: [CarPlayHuddleIdeaEntry] = [],
        chronicleSummary: CarPlayChronicleSummary = CarPlayChronicleSummary(),
        chronicleReviews: [CarPlayChronicleReviewEntry] = [],
        recentActivity: [CarPlayActivityEntry] = [],
        missionSummary: CarPlayMissionSummary,
        agentSummary: CarPlayAgentSummary,
        counts: CarPlayOpsCounts = CarPlayOpsCounts()
    ) {
        self.generatedAt = generatedAt
        self.currentFocus = currentFocus
        self.focusCandidates = focusCandidates
        self.approvals = approvals
        self.recoveryCases = recoveryCases
        self.agentOps = agentOps
        self.supervisionItems = supervisionItems
        self.huddleSummary = huddleSummary
        self.huddleIdeas = huddleIdeas
        self.chronicleSummary = chronicleSummary
        self.chronicleReviews = chronicleReviews
        self.recentActivity = recentActivity
        self.missionSummary = missionSummary
        self.agentSummary = agentSummary
        self.counts = counts
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        generatedAt = try container.decodeIfPresent(String.self, forKey: .generatedAt) ?? ""
        currentFocus = try container.decode(CarPlayProgressFocus.self, forKey: .currentFocus)
        focusCandidates = try container.decodeIfPresent([CarPlayOpsFocusCandidate].self, forKey: .focusCandidates) ?? []
        approvals = try container.decodeIfPresent([CarPlayApprovalEntry].self, forKey: .approvals) ?? []
        recoveryCases = try container.decodeIfPresent([CarPlayRecoveryCaseEntry].self, forKey: .recoveryCases) ?? []
        agentOps = try container.decodeIfPresent([CarPlayAgentOpsEntry].self, forKey: .agentOps) ?? []
        supervisionItems = try container.decodeIfPresent([CarPlaySupervisionEntry].self, forKey: .supervisionItems) ?? []
        huddleSummary = try container.decode(CarPlayHuddleSummary.self, forKey: .huddleSummary)
        huddleIdeas = try container.decodeIfPresent([CarPlayHuddleIdeaEntry].self, forKey: .huddleIdeas) ?? []
        chronicleSummary = try container.decodeIfPresent(CarPlayChronicleSummary.self, forKey: .chronicleSummary) ?? CarPlayChronicleSummary()
        chronicleReviews = try container.decodeIfPresent([CarPlayChronicleReviewEntry].self, forKey: .chronicleReviews) ?? []
        recentActivity = try container.decodeIfPresent([CarPlayActivityEntry].self, forKey: .recentActivity) ?? []
        missionSummary = try container.decode(CarPlayMissionSummary.self, forKey: .missionSummary)
        agentSummary = try container.decode(CarPlayAgentSummary.self, forKey: .agentSummary)
        counts = try container.decodeIfPresent(CarPlayOpsCounts.self, forKey: .counts) ?? CarPlayOpsCounts()
    }
}

public struct CarPlayNavigationChoice: Equatable, Identifiable, Sendable {
    public enum Source: String, Equatable, Sendable {
        case saved
        case favorite
        case recent
        case routeHistory = "route_history"
    }

    public let id: String
    public let title: String
    public let detail: String
    public let destination: String
    public let source: Source

    public init(
        id: String,
        title: String,
        detail: String,
        destination: String,
        source: Source
    ) {
        self.id = id
        self.title = title
        self.detail = detail
        self.destination = destination
        self.source = source
    }
}

public struct CarPlayPublishQueueEntry: Equatable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let detail: String
    public let stageDisplay: String

    public init(id: String, title: String, detail: String, stageDisplay: String) {
        self.id = id
        self.title = title
        self.detail = detail
        self.stageDisplay = stageDisplay
    }
}

public enum JarvisCarPlayPresentation {
    public static func preferredOriginLabel(from overview: NavigationLocationsOverview) -> String {
        let state = overview.navigationState
        if state?.selectedOriginMode.lowercased() == "current" {
            return "Current Location"
        }
        if let preferredId = overview.preferredLocationId,
           let preferred = overview.savedLocations.first(where: { $0.id == preferredId }) {
            return preferred.address.isEmpty ? preferred.label : preferred.address
        }
        if let selectedId = state?.selectedSavedLocationID,
           let selected = overview.savedLocations.first(where: { $0.id == selectedId }) {
            return selected.address.isEmpty ? selected.label : selected.address
        }
        if let first = overview.savedLocations.first {
            return first.address.isEmpty ? first.label : first.address
        }
        return "Home"
    }

    public static func navigationChoices(
        from overview: NavigationLocationsOverview,
        limit: Int = 8
    ) -> [CarPlayNavigationChoice] {
        var seenDestinations = Set<String>()
        var seenTitles = Set<String>()
        var choices: [CarPlayNavigationChoice] = []

        func appendChoice(
            id: String,
            title: String,
            detail: String,
            destination: String,
            source: CarPlayNavigationChoice.Source
        ) {
            let trimmedDestination = destination.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmedDestination.isEmpty else { return }
            let dedupeKey = trimmedDestination.lowercased()
            let titleKey = title.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
            guard !seenDestinations.contains(dedupeKey), !seenTitles.contains(titleKey) else { return }
            seenDestinations.insert(dedupeKey)
            seenTitles.insert(titleKey)
            choices.append(
                CarPlayNavigationChoice(
                    id: id,
                    title: title,
                    detail: detail,
                    destination: trimmedDestination,
                    source: source
                )
            )
        }

        for location in overview.savedLocations {
            appendChoice(
                id: "saved:\(location.id)",
                title: location.label,
                detail: location.address.isEmpty ? location.geography : location.address,
                destination: location.address.isEmpty ? location.label : location.address,
                source: .saved
            )
        }

        for favorite in overview.navigationState?.favoriteDestinations ?? [] {
            appendChoice(
                id: "favorite:\(favorite)",
                title: favorite,
                detail: "Favorite destination",
                destination: favorite,
                source: .favorite
            )
        }

        for recent in overview.navigationState?.recentDestinations ?? [] {
            appendChoice(
                id: "recent:\(recent)",
                title: recent,
                detail: "Recent destination",
                destination: recent,
                source: .recent
            )
        }

        for route in overview.navigationState?.routeHistory ?? [] {
            appendChoice(
                id: "route-history:\(route.routeID)",
                title: route.destination,
                detail: "\(route.origin) -> \(route.destination)",
                destination: route.destination,
                source: .routeHistory
            )
        }

        return Array(choices.prefix(limit))
    }

    public static func currentRouteHeadline(
        state: NavigationState?,
        route: NavigationRouteOverview?
    ) -> (title: String, detail: String)? {
        let origin = route?.origin.label ?? state?.lastRoute.origin ?? ""
        let destination = route?.destination.label ?? state?.lastRoute.destination ?? ""
        guard !origin.isEmpty, !destination.isEmpty else { return nil }

        let detailParts = [
            route?.summary,
            route.flatMap { routeDetail(for: $0) },
        ]
            .compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }

        return (
            title: "\(origin) -> \(destination)",
            detail: detailParts.joined(separator: " · ")
        )
    }

    public static func routeDetail(for route: NavigationRouteOverview) -> String {
        var details: [String] = []
        if let distance = route.route.distanceMiles {
            details.append(String(format: "%.0f mi", distance))
        }
        if let duration = route.route.durationMinutes {
            details.append("\(duration) min")
        }
        if route.hazardActive {
            details.append("Hazard active")
        }
        return details.joined(separator: " · ")
    }

    public static func publishQueue(
        from overview: PublishOverview,
        limit: Int = 6
    ) -> [CarPlayPublishQueueEntry] {
        Array(overview.pendingReviews.prefix(limit)).map { review in
            let stage = review.stageDisplay.isEmpty ? review.stageKey : review.stageDisplay
            let summaryBits = [
                stage.trimmingCharacters(in: .whitespacesAndNewlines),
                review.wordCount > 0 ? "\(review.wordCount) words" : "",
                review.readySince.isEmpty ? "" : review.readySince,
            ].filter { !$0.isEmpty }
            return CarPlayPublishQueueEntry(
                id: review.id,
                title: review.title,
                detail: summaryBits.joined(separator: " · "),
                stageDisplay: stage
            )
        }
    }
}
