import Foundation

/// Aggregated settings/admin overview returned by GET /api/apple/systems/admin-summary
public struct SystemsAdminSummary: Codable, Sendable {
    public let accounts: SystemsAdminAccounts
    public let family: SystemsAdminFamily
    public let devices: SystemsAdminDevices
    public let voice: SystemsAdminVoice
    public let service: SystemsAdminService
    public let integrations: SystemsAdminIntegrations
    public let costs: SystemsAdminCosts
    public let governance: SystemsAdminGovernance
    public let sandboxOperations: SystemsAdminSandboxOperations
    public let reflectiveMemory: SystemsAdminReflectiveMemory
    public let governedWorkflows: SystemsAdminGovernedWorkflows

    enum CodingKeys: String, CodingKey {
        case accounts, family, devices, voice, service, integrations, costs, governance
        case sandboxOperations = "sandbox_operations"
        case reflectiveMemory = "reflective_memory"
        case governedWorkflows = "governed_workflows"
    }
}

public struct SystemsAdminAccounts: Codable, Sendable {
    public let total: Int
    public let connected: Int
    public let planned: Int
    public let items: [SystemsAdminAccountItem]
}

public struct SystemsAdminAccountItem: Codable, Sendable, Identifiable {
    public let id: String
    public let label: String
    public let provider: String
    public let status: String
    public let loginHint: String
    public let serviceScope: String
    public let notes: String
    public let connectionStatus: String
    public let detail: String

    enum CodingKeys: String, CodingKey {
        case id, label, provider, status, detail, notes
        case loginHint = "login_hint"
        case serviceScope = "service_scope"
        case connectionStatus = "connection_status"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        label = try container.decode(String.self, forKey: .label)
        provider = try container.decode(String.self, forKey: .provider)
        status = try container.decode(String.self, forKey: .status)
        loginHint = try container.decodeIfPresent(String.self, forKey: .loginHint) ?? ""
        serviceScope = try container.decodeIfPresent(String.self, forKey: .serviceScope) ?? "mail_calendar"
        notes = try container.decodeIfPresent(String.self, forKey: .notes) ?? ""
        connectionStatus = try container.decodeIfPresent(String.self, forKey: .connectionStatus) ?? status
        detail = try container.decodeIfPresent(String.self, forKey: .detail) ?? notes
    }
}

public struct SystemsAccountActionResult: Codable, Sendable {
    public let message: String
    public let account: SystemsAdminAccountItem
    public let focus: SystemsProfileFocus?

    public init(message: String, account: SystemsAdminAccountItem, focus: SystemsProfileFocus?) {
        self.message = message
        self.account = account
        self.focus = focus
    }
}

public struct SystemsAdminFamily: Codable, Sendable {
    public let memberCount: Int
    public let onlineCount: Int
    public let members: [SystemsAdminFamilyMember]

    enum CodingKeys: String, CodingKey {
        case members
        case memberCount = "member_count"
        case onlineCount = "online_count"
    }
}

public struct SystemsAdminFamilyMember: Codable, Sendable, Identifiable {
    public let id: String
    public let displayName: String
    public let role: String
    public let permissions: String
    public let trustLevel: String
    public let preferredTone: String
    public let privacyBoundary: String
    public let notes: String
    public let deviceCount: Int
    public let onlineDeviceCount: Int
    public let status: String

    enum CodingKeys: String, CodingKey {
        case id, role, permissions, status, notes
        case displayName = "display_name"
        case trustLevel = "trust_level"
        case preferredTone = "preferred_tone"
        case privacyBoundary = "privacy_boundary"
        case deviceCount = "device_count"
        case onlineDeviceCount = "online_device_count"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        displayName = try container.decode(String.self, forKey: .displayName)
        role = try container.decodeIfPresent(String.self, forKey: .role) ?? ""
        permissions = try container.decodeIfPresent(String.self, forKey: .permissions) ?? ""
        trustLevel = try container.decodeIfPresent(String.self, forKey: .trustLevel) ?? "standard"
        preferredTone = try container.decodeIfPresent(String.self, forKey: .preferredTone) ?? ""
        privacyBoundary = try container.decodeIfPresent(String.self, forKey: .privacyBoundary) ?? "personal"
        notes = try container.decodeIfPresent(String.self, forKey: .notes) ?? ""
        deviceCount = try container.decodeIfPresent(Int.self, forKey: .deviceCount) ?? 0
        onlineDeviceCount = try container.decodeIfPresent(Int.self, forKey: .onlineDeviceCount) ?? 0
        status = try container.decodeIfPresent(String.self, forKey: .status) ?? "Unknown"
    }
}

public struct SystemsFamilyMemberActionResult: Codable, Sendable {
    public let message: String
    public let member: SystemsAdminFamilyMember
    public let focus: SystemsProfileFocus?

    public init(message: String, member: SystemsAdminFamilyMember, focus: SystemsProfileFocus?) {
        self.message = message
        self.member = member
        self.focus = focus
    }
}

public struct SystemsAdminDevices: Codable, Sendable {
    public let total: Int
    public let mappedCount: Int
    public let sharedCount: Int
    public let items: [SystemsAdminDeviceItem]

    enum CodingKeys: String, CodingKey {
        case total, items
        case mappedCount = "mapped_count"
        case sharedCount = "shared_count"
    }
}

public struct SystemsAdminDeviceItem: Codable, Sendable, Identifiable {
    public let id: String
    public let label: String
    public let ownerName: String
    public let lastSeenAt: String
    public let mapped: Bool
    public let shared: Bool
    public let status: String

    enum CodingKeys: String, CodingKey {
        case id, label, mapped, shared, status
        case ownerName = "owner_name"
        case lastSeenAt = "last_seen_at"
    }
}

public struct SystemsAdminVoice: Codable, Sendable {
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

public struct SystemsAdminService: Codable, Sendable {
    public let hostname: String
    public let lanURL: String
    public let deploymentMode: String
    public let modeLabel: String
    public let hostedBaseURL: String
    public let hostedProvider: String
    public let edgeProvider: String
    public let remoteAdminHost: String
    public let cloudflareAccessEnabled: Bool
    public let tunnelEnabled: Bool
    public let publicRouteCount: Int
    public let composeServiceCount: Int
    public let runtimeLoaded: Bool
    public let openvikingLoaded: Bool
    public let assistantLoaded: Bool

    enum CodingKeys: String, CodingKey {
        case hostname
        case lanURL = "lan_url"
        case deploymentMode = "deployment_mode"
        case modeLabel = "mode_label"
        case hostedBaseURL = "hosted_base_url"
        case hostedProvider = "hosted_provider"
        case edgeProvider = "edge_provider"
        case remoteAdminHost = "remote_admin_host"
        case cloudflareAccessEnabled = "cloudflare_access_enabled"
        case tunnelEnabled = "tunnel_enabled"
        case publicRouteCount = "public_route_count"
        case composeServiceCount = "compose_service_count"
        case runtimeLoaded = "runtime_loaded"
        case openvikingLoaded = "openviking_loaded"
        case assistantLoaded = "assistant_loaded"
    }
}

public struct SystemsAdminIntegrations: Codable, Sendable {
    public let googleReady: Bool
    public let googleConnectedCount: Int
    public let googleClientSecretPresent: Bool
    public let microsoftReady: Bool
    public let microsoftConnectedCount: Int

    enum CodingKeys: String, CodingKey {
        case googleReady = "google_ready"
        case googleConnectedCount = "google_connected_count"
        case googleClientSecretPresent = "google_client_secret_present"
        case microsoftReady = "microsoft_ready"
        case microsoftConnectedCount = "microsoft_connected_count"
    }
}

public struct SystemsAdminCosts: Codable, Sendable {
    public let windowHours: Int
    public let monthTotalUSD: Double
    public let totalCalls: Int
    public let paidCalls: Int
    public let promptTokens: Int
    public let completionTokens: Int
    public let models: [SystemsAdminCostModel]

    enum CodingKeys: String, CodingKey {
        case models
        case windowHours = "window_hours"
        case monthTotalUSD = "month_total_usd"
        case totalCalls = "total_calls"
        case paidCalls = "paid_calls"
        case promptTokens = "prompt_tokens"
        case completionTokens = "completion_tokens"
    }
}

public struct SystemsAdminCostModel: Codable, Sendable, Identifiable {
    public let id: String
    public let name: String
    public let backend: String
    public let calls: Int
    public let costUSD: Double

    enum CodingKeys: String, CodingKey {
        case id, name, backend, calls
        case costUSD = "cost_usd"
    }
}

public struct SystemsAdminGovernance: Codable, Sendable {
    public let zoneCount: Int
    public let activeZoneCount: Int
    public let arenaCount: Int
    public let activeArenaCount: Int
    public let stageCount: Int
    public let pendingQueueCount: Int
    public let promotionRecordCount: Int
    public let zones: [SystemsAdminGovernanceZone]
    public let arenas: [SystemsAdminGovernanceArena]
    public let stages: [SystemsAdminGovernanceStage]
    public let queue: [SystemsAdminGovernanceQueueItem]
    public let promotionRecords: [SystemsAdminGovernancePromotionRecord]

    enum CodingKeys: String, CodingKey {
        case zones, arenas, stages, queue
        case promotionRecords = "promotion_records"
        case zoneCount = "zone_count"
        case activeZoneCount = "active_zone_count"
        case arenaCount = "arena_count"
        case activeArenaCount = "active_arena_count"
        case stageCount = "stage_count"
        case pendingQueueCount = "pending_queue_count"
        case promotionRecordCount = "promotion_record_count"
    }
}

public struct SystemsAdminGovernanceZone: Codable, Sendable, Identifiable {
    public let id: String
    public let name: String
    public let zoneType: String
    public let authorityStage: String
    public let approvalMode: String
    public let status: String
    public let actionCount: Int

    enum CodingKeys: String, CodingKey {
        case id, name, status
        case zoneType = "zone_type"
        case authorityStage = "authority_stage"
        case approvalMode = "approval_mode"
        case actionCount = "action_count"
    }
}

public struct SystemsAdminGovernanceArena: Codable, Sendable, Identifiable {
    public let id: String
    public let name: String
    public let resourceType: String
    public let linkedZoneId: String
    public let riskClass: String
    public let status: String

    enum CodingKeys: String, CodingKey {
        case id, name, status
        case resourceType = "resource_type"
        case linkedZoneId = "linked_zone_id"
        case riskClass = "risk_class"
    }
}

public struct SystemsAdminGovernanceStage: Codable, Sendable, Identifiable {
    public let id: String
    public let name: String
    public let sequence: Int
    public let status: String
    public let actionTypeCount: Int
    public let boundaryMode: String

    enum CodingKeys: String, CodingKey {
        case id, name, sequence, status
        case actionTypeCount = "action_type_count"
        case boundaryMode = "boundary_mode"
    }
}

public struct SystemsAdminGovernanceQueueItem: Codable, Sendable, Identifiable {
    public let id: String
    public let arenaId: String
    public let actionType: String
    public let status: String
    public let createdAt: String
    public let principalId: String
    public let draftId: String

    enum CodingKeys: String, CodingKey {
        case id, status
        case arenaId = "arena_id"
        case actionType = "action_type"
        case createdAt = "created_at"
        case principalId = "principal_id"
        case draftId = "draft_id"
    }
}

public struct SystemsAdminGovernancePromotionRecord: Codable, Sendable, Identifiable {
    public let id: String
    public let eventType: String
    public let subjectKind: String
    public let subjectId: String
    public let status: String
    public let actor: String
    public let basis: String
    public let trustZone: String
    public let arenaId: String
    public let authorityStage: String
    public let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, status, actor, basis
        case eventType = "event_type"
        case subjectKind = "subject_kind"
        case subjectId = "subject_id"
        case trustZone = "trust_zone"
        case arenaId = "arena_id"
        case authorityStage = "authority_stage"
        case createdAt = "created_at"
    }
}

public struct SystemsTrustZoneActionResult: Codable, Sendable {
    public let status: String
    public let zoneId: String
    public let authorityStage: String
    public let approvalMode: String

    enum CodingKeys: String, CodingKey {
        case status
        case zoneId = "zone_id"
        case authorityStage = "authority_stage"
        case approvalMode = "approval_mode"
    }
}

public struct SystemsArenaActionResult: Codable, Sendable {
    public let status: String
    public let arenaId: String
    public let linkedZoneId: String

    enum CodingKeys: String, CodingKey {
        case status
        case arenaId = "arena_id"
        case linkedZoneId = "linked_zone_id"
    }
}

public struct SystemsAdminSandboxOperations: Codable, Sendable {
    public let queue: SystemsAdminSandboxQueue
    public let jobs: [SystemsAdminSandboxJob]
    public let activeRuns: [SystemsAdminSandboxActiveRun]
    public let recentRuns: [SystemsAdminSandboxRecentRun]
    public let laneSummaries: [SystemsAdminSandboxLaneSummary]

    enum CodingKeys: String, CodingKey {
        case jobs
        case queue
        case activeRuns = "active_runs"
        case recentRuns = "recent_runs"
        case laneSummaries = "lane_summaries"
    }
}

public struct SystemsAdminSandboxQueue: Codable, Sendable {
    public let activeCount: Int
    public let queuedJobCount: Int
    public let reviewReadyCount: Int
    public let failedRunCount: Int
    public let activeJobs: [String]
    public let laneCount: Int

    enum CodingKeys: String, CodingKey {
        case activeCount = "active_count"
        case queuedJobCount = "queued_job_count"
        case reviewReadyCount = "review_ready_count"
        case failedRunCount = "failed_run_count"
        case activeJobs = "active_jobs"
        case laneCount = "lane_count"
    }
}

public struct SystemsAdminSandboxJob: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let status: String
    public let jobType: String
    public let target: String
    public let reviewLevel: String
    public let summary: String
    public let autoAllowed: Bool
    public let updatedAt: String
    public let lastSandboxRunId: String

    enum CodingKeys: String, CodingKey {
        case id, title, status, target, summary
        case jobId = "job_id"
        case jobType = "job_type"
        case reviewLevel = "review_level"
        case autoAllowed = "auto_allowed"
        case updatedAt = "updated_at"
        case lastSandboxRunId = "last_sandbox_run_id"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.id = try container.decodeIfPresent(String.self, forKey: .jobId)
            ?? container.decode(String.self, forKey: .id)
        self.title = try container.decode(String.self, forKey: .title)
        self.status = try container.decode(String.self, forKey: .status)
        self.jobType = try container.decode(String.self, forKey: .jobType)
        self.target = try container.decode(String.self, forKey: .target)
        self.reviewLevel = try container.decode(String.self, forKey: .reviewLevel)
        self.summary = try container.decode(String.self, forKey: .summary)
        self.autoAllowed = try container.decode(Bool.self, forKey: .autoAllowed)
        self.updatedAt = try container.decode(String.self, forKey: .updatedAt)
        self.lastSandboxRunId = try container.decode(String.self, forKey: .lastSandboxRunId)
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .jobId)
        try container.encode(title, forKey: .title)
        try container.encode(status, forKey: .status)
        try container.encode(jobType, forKey: .jobType)
        try container.encode(target, forKey: .target)
        try container.encode(reviewLevel, forKey: .reviewLevel)
        try container.encode(summary, forKey: .summary)
        try container.encode(autoAllowed, forKey: .autoAllowed)
        try container.encode(updatedAt, forKey: .updatedAt)
        try container.encode(lastSandboxRunId, forKey: .lastSandboxRunId)
    }
}

public struct SystemsAdminSandboxActiveRun: Codable, Sendable, Identifiable {
    public let id: String
    public let jobId: String
    public let title: String
    public let status: String
    public let currentStep: String
    public let message: String
    public let updatedAt: String
    public let worktreePath: String

    enum CodingKeys: String, CodingKey {
        case id, title, status, message
        case jobId = "job_id"
        case currentStep = "current_step"
        case updatedAt = "updated_at"
        case worktreePath = "worktree_path"
    }
}

public struct SystemsAdminSandboxRecentRun: Codable, Sendable, Identifiable {
    public let id: String
    public let jobId: String
    public let title: String
    public let generatedAt: String
    public let mode: String
    public let compileOK: Bool
    public let testsOK: Bool
    public let reportPath: String
    public let patchBundlePath: String

    enum CodingKeys: String, CodingKey {
        case id, mode
        case jobId = "job_id"
        case title = "title"
        case generatedAt = "generated_at"
        case compileOK = "compile_ok"
        case testsOK = "tests_ok"
        case reportPath = "report_path"
        case patchBundlePath = "patch_bundle_path"
    }
}

public struct SystemsAdminSandboxLaneSummary: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let queuedCount: Int
    public let activeRunCount: Int
    public let reviewReadyCount: Int
    public let failedRunCount: Int
    public let lastJobId: String
    public let status: String
    public let detail: String

    enum CodingKeys: String, CodingKey {
        case id, title, status, detail
        case queuedCount = "queued_count"
        case activeRunCount = "active_run_count"
        case reviewReadyCount = "review_ready_count"
        case failedRunCount = "failed_run_count"
        case lastJobId = "last_job_id"
    }
}

public struct SystemsSandboxJobActionResult: Codable, Sendable {
    public let ok: Bool
    public let accepted: Bool
    public let mode: String
    public let jobId: String
    public let status: String
    public let message: String
    public let activeRunId: String
    public let queueActiveCount: Int

    enum CodingKeys: String, CodingKey {
        case ok, accepted, mode, status, message
        case jobId = "job_id"
        case activeRunId = "active_run_id"
        case queueActiveCount = "queue_active_count"
    }
}

public struct SystemsAdminReflectiveMemory: Codable, Sendable {
    public let subjectDisplayName: String
    public let profileFactCount: Int
    public let pendingProposalCount: Int
    public let firstLightHistoryCount: Int
    public let insightCount: Int
    public let activeInsightCount: Int
    public let stewardshipDecisionCount: Int
    public let governanceLearningCount: Int
    public let preferredTone: String
    public let briefingStyle: String
    public let preferredVoice: String
    public let guidanceLines: [String]
    public let profileFacts: [SystemsAdminReflectiveFact]
    public let pendingProposals: [SystemsAdminReflectiveProposal]
    public let recentFirstLight: [SystemsAdminReflectiveFirstLight]
    public let recentStewardshipDecisions: [SystemsAdminReflectiveFirstLight]
    public let governanceLearning: [SystemsAdminGovernanceLearningItem]
    public let memoryGraph: SystemsAdminMemoryGraph

    enum CodingKeys: String, CodingKey {
        case guidanceLines = "guidance_lines"
        case profileFacts = "profile_facts"
        case pendingProposals = "pending_proposals"
        case recentFirstLight = "recent_first_light"
        case recentStewardshipDecisions = "recent_stewardship_decisions"
        case governanceLearning = "governance_learning"
        case memoryGraph = "memory_graph"
        case subjectDisplayName = "subject_display_name"
        case profileFactCount = "profile_fact_count"
        case pendingProposalCount = "pending_proposal_count"
        case firstLightHistoryCount = "first_light_history_count"
        case insightCount = "insight_count"
        case activeInsightCount = "active_insight_count"
        case stewardshipDecisionCount = "stewardship_decision_count"
        case governanceLearningCount = "governance_learning_count"
        case preferredTone = "preferred_tone"
        case briefingStyle = "briefing_style"
        case preferredVoice = "preferred_voice"
    }
}

public struct SystemsAdminMemoryGraph: Codable, Sendable {
    public let subjectDisplayName: String
    public let preferredTone: String
    public let briefingStyle: String
    public let preferredVoice: String
    public let anchorCount: Int
    public let threadCount: Int
    public let coverageCount: Int
    public let horizonCount: Int
    public let anchors: [SystemsAdminMemoryAnchor]
    public let activeThreads: [SystemsAdminMemoryThread]
    public let surfaceCoverage: [SystemsAdminMemoryCoverage]
    public let horizons: [SystemsAdminMemoryHorizon]
    public let guidanceLines: [String]

    enum CodingKeys: String, CodingKey {
        case guidanceLines = "guidance_lines"
        case anchorCount = "anchor_count"
        case threadCount = "thread_count"
        case coverageCount = "coverage_count"
        case horizonCount = "horizon_count"
        case activeThreads = "active_threads"
        case surfaceCoverage = "surface_coverage"
        case subjectDisplayName = "subject_display_name"
        case preferredTone = "preferred_tone"
        case briefingStyle = "briefing_style"
        case preferredVoice = "preferred_voice"
        case anchors, horizons
    }
}

public struct SystemsAdminMemoryAnchor: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let summary: String
    public let signalCount: Int
    public let lastSignal: String

    enum CodingKeys: String, CodingKey {
        case id, title, summary
        case signalCount = "signal_count"
        case lastSignal = "last_signal"
    }
}

public struct SystemsAdminMemoryThread: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let summary: String
    public let horizon: String
    public let signalCount: Int

    enum CodingKeys: String, CodingKey {
        case id, title, summary, horizon
        case signalCount = "signal_count"
    }
}

public struct SystemsAdminMemoryCoverage: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let status: String
    public let detail: String
}

public struct SystemsAdminMemoryHorizon: Codable, Sendable, Identifiable {
    public let id: String
    public let label: String
    public let windowDays: Int
    public let profileFactCount: Int
    public let chronicleEntryCount: Int
    public let firstLightCount: Int
    public let stewardshipDecisionCount: Int
    public let summary: String

    enum CodingKeys: String, CodingKey {
        case id, label, summary
        case windowDays = "window_days"
        case profileFactCount = "profile_fact_count"
        case chronicleEntryCount = "chronicle_entry_count"
        case firstLightCount = "first_light_count"
        case stewardshipDecisionCount = "stewardship_decision_count"
    }
}

public struct SystemsAdminGovernanceLearningItem: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let summary: String
    public let recommendation: String
    public let confidence: String
}

public struct SystemsAdminReflectiveFact: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let summary: String
    public let tags: [String]
    public let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case id, title, summary, tags
        case updatedAt = "updated_at"
    }
}

public struct SystemsAdminReflectiveProposal: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let summary: String
    public let status: String
    public let memoryType: String
    public let confidence: String

    enum CodingKeys: String, CodingKey {
        case id, title, summary, status, confidence
        case memoryType = "memory_type"
    }
}

public struct SystemsAdminReflectiveFirstLight: Codable, Sendable, Identifiable {
    public let id: String
    public let label: String
    public let summary: String
}

public struct SystemsAdminGovernedWorkflows: Codable, Sendable {
    public let pendingApprovalCount: Int
    public let rejectedApprovalCount: Int
    public let automaticActionCount: Int
    public let frictionActionCount: Int
    public let doctrineCandidateCount: Int
    public let governanceProposalCount: Int
    public let activeRuleCount: Int
    public let stagedStewardshipReviewCount: Int
    public let stagedCalendarRouteCount: Int
    public let pendingApprovals: [SystemsAdminApprovalItem]
    public let recentActions: [SystemsAdminGovernedActionItem]
    public let recentStewardshipReviews: [SystemsAdminStewardshipReviewItem]
    public let recentCalendarRoutes: [SystemsAdminCalendarRouteItem]
    public let governanceProposals: [SystemsAdminDoctrineCandidateItem]
    public let doctrineCandidates: [SystemsAdminDoctrineCandidateItem]

    enum CodingKeys: String, CodingKey {
        case pendingApprovals = "pending_approvals"
        case recentActions = "recent_actions"
        case recentStewardshipReviews = "recent_stewardship_reviews"
        case recentCalendarRoutes = "recent_calendar_routes"
        case governanceProposals = "governance_proposals"
        case doctrineCandidates = "doctrine_candidates"
        case pendingApprovalCount = "pending_approval_count"
        case rejectedApprovalCount = "rejected_approval_count"
        case automaticActionCount = "automatic_action_count"
        case frictionActionCount = "friction_action_count"
        case doctrineCandidateCount = "doctrine_candidate_count"
        case governanceProposalCount = "governance_proposal_count"
        case activeRuleCount = "active_rule_count"
        case stagedStewardshipReviewCount = "staged_stewardship_review_count"
        case stagedCalendarRouteCount = "staged_calendar_route_count"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        pendingApprovalCount = try container.decodeIfPresent(Int.self, forKey: .pendingApprovalCount) ?? 0
        rejectedApprovalCount = try container.decodeIfPresent(Int.self, forKey: .rejectedApprovalCount) ?? 0
        automaticActionCount = try container.decodeIfPresent(Int.self, forKey: .automaticActionCount) ?? 0
        frictionActionCount = try container.decodeIfPresent(Int.self, forKey: .frictionActionCount) ?? 0
        doctrineCandidateCount = try container.decodeIfPresent(Int.self, forKey: .doctrineCandidateCount) ?? 0
        governanceProposalCount = try container.decodeIfPresent(Int.self, forKey: .governanceProposalCount) ?? 0
        activeRuleCount = try container.decodeIfPresent(Int.self, forKey: .activeRuleCount) ?? 0
        stagedStewardshipReviewCount = try container.decodeIfPresent(Int.self, forKey: .stagedStewardshipReviewCount) ?? 0
        stagedCalendarRouteCount = try container.decodeIfPresent(Int.self, forKey: .stagedCalendarRouteCount) ?? 0
        pendingApprovals = try container.decodeIfPresent([SystemsAdminApprovalItem].self, forKey: .pendingApprovals) ?? []
        recentActions = try container.decodeIfPresent([SystemsAdminGovernedActionItem].self, forKey: .recentActions) ?? []
        recentStewardshipReviews = try container.decodeIfPresent([SystemsAdminStewardshipReviewItem].self, forKey: .recentStewardshipReviews) ?? []
        recentCalendarRoutes = try container.decodeIfPresent([SystemsAdminCalendarRouteItem].self, forKey: .recentCalendarRoutes) ?? []
        governanceProposals = try container.decodeIfPresent([SystemsAdminDoctrineCandidateItem].self, forKey: .governanceProposals) ?? []
        doctrineCandidates = try container.decodeIfPresent([SystemsAdminDoctrineCandidateItem].self, forKey: .doctrineCandidates) ?? []
    }
}

public struct GovernanceProposalActionResult: Codable, Sendable {
    public let proposalId: String
    public let candidateId: String
    public let title: String
    public let status: String
    public let performedAction: String
    public let message: String
    public let ruleId: String

    enum CodingKeys: String, CodingKey {
        case title, status, message
        case proposalId = "proposal_id"
        case candidateId = "candidate_id"
        case performedAction = "performed_action"
        case ruleId = "rule_id"
    }
}

public struct SystemsAdminApprovalItem: Codable, Sendable, Identifiable {
    public let id: String
    public let actor: String
    public let request: String
    public let status: String
    public let rationale: String
    public let timestamp: String
}

public struct SystemsAdminGovernedActionItem: Codable, Sendable, Identifiable {
    public let id: String
    public let domain: String
    public let action: String
    public let decision: String
    public let mode: String
    public let succeeded: Bool
    public let causedFriction: Bool
    public let whyNow: String
    public let timestamp: String

    enum CodingKeys: String, CodingKey {
        case id, domain, action, decision, mode, succeeded
        case whyNow = "why_now"
        case timestamp
        case causedFriction = "caused_friction"
    }
}

public struct SystemsAdminStewardshipReviewItem: Codable, Sendable, Identifiable {
    public let id: String
    public let laneId: String
    public let laneTitle: String
    public let status: String
    public let reviewSurface: String
    public let packetTarget: String
    public let boundaryDecision: String
    public let boundaryReason: String
    public let approvalMode: String
    public let sandboxJobId: String
    public let timestamp: String

    enum CodingKeys: String, CodingKey {
        case id, status, timestamp
        case laneId = "lane_id"
        case laneTitle = "lane_title"
        case reviewSurface = "review_surface"
        case packetTarget = "packet_target"
        case boundaryDecision = "boundary_decision"
        case boundaryReason = "boundary_reason"
        case approvalMode = "approval_mode"
        case sandboxJobId = "sandbox_job_id"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        laneId = try container.decode(String.self, forKey: .laneId)
        laneTitle = try container.decode(String.self, forKey: .laneTitle)
        status = try container.decode(String.self, forKey: .status)
        reviewSurface = try container.decode(String.self, forKey: .reviewSurface)
        packetTarget = try container.decode(String.self, forKey: .packetTarget)
        boundaryDecision = try container.decode(String.self, forKey: .boundaryDecision)
        boundaryReason = try container.decode(String.self, forKey: .boundaryReason)
        approvalMode = try container.decode(String.self, forKey: .approvalMode)
        sandboxJobId = try container.decodeIfPresent(String.self, forKey: .sandboxJobId) ?? ""
        timestamp = try container.decode(String.self, forKey: .timestamp)
    }
}

public struct SystemsAdminCalendarRouteItem: Codable, Sendable, Identifiable {
    public let id: String
    public let eventId: String
    public let title: String
    public let status: String
    public let location: String
    public let reviewLevel: String
    public let summary: String
    public let sandboxJobId: String
    public let timestamp: String

    enum CodingKeys: String, CodingKey {
        case id, title, status, location, summary, timestamp
        case eventId = "event_id"
        case reviewLevel = "review_level"
        case sandboxJobId = "sandbox_job_id"
    }
}

public struct SystemsAdminDoctrineCandidateItem: Codable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let kind: String
    public let status: String
    public let summary: String
    public let promotionReason: String

    enum CodingKeys: String, CodingKey {
        case id, title, kind, status, summary
        case promotionReason = "promotion_reason"
    }
}
