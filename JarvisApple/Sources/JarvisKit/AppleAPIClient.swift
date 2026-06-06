import Foundation

// MARK: - AppleAPIClient

/// Shared JARVIS API client for JarvisPhone, JarvisWatch, and JarvisMac.
///
/// All network calls use Swift Concurrency (`async/await`).  The client reads
/// its base URL from `JARVISEnvironment.baseURL` on every call so that
/// switching environments at runtime is reflected immediately.
///
/// Usage:
/// ```swift
/// let briefing = try await AppleAPIClient.shared.fetchBriefing()
/// ```
public final class AppleAPIClient: Sendable {

    // MARK: - Singleton

    public static let shared = AppleAPIClient()

    // MARK: - Init

    private init() {}

    // MARK: - Computed base URL

    private var baseURL: URL { JARVISEnvironment.baseURL }

    // MARK: - Briefing

    /// Fetch the full 5-zone Chamber home-screen packet.
    public func fetchBriefing(actor: String = "chris") async throws -> BriefingPacket {
        try await get("/api/apple/briefing?actor=\(actor)")
    }

    public func applyBriefingOpenLoopAction(
        itemId: String,
        domain: String,
        action: String,
        title: String,
        summary: String,
        note: String = "",
        actor: String = "chris"
    ) async throws -> BriefingOpenLoopActionResult {
        struct Body: Encodable {
            let actor: String
            let domain: String
            let action: String
            let title: String
            let summary: String
            let note: String
        }
        return try await post(
            "/api/apple/briefing/open-loops/\(itemId)/action",
            body: Body(actor: actor, domain: domain, action: action, title: title, summary: summary, note: note)
        )
    }

    /// Fetch the compact Watch complication status payload.
    public func fetchStatus() async throws -> WatchStatus {
        try await get("/api/apple/status")
    }

    public func fetchAppState() async throws -> AppStateOverview {
        try await get("/api/apple/app-state")
    }

    /// Fetch live server-side Storm weather. This does not require iPhone
    /// location permission and is the preferred fallback for the Weather tab.
    public func fetchAppleWeather() async throws -> AppleWeatherOverview {
        try await get("/api/apple/weather")
    }

    public func fetchNavigationLocations() async throws -> NavigationLocationsOverview {
        try await get("/api/apple/navigation/locations")
    }

    public func fetchNavigationState() async throws -> NavigationState {
        try await get("/api/apple/navigation/state")
    }

    public func updateNavigationState(_ state: NavigationStatePatch) async throws -> NavigationState {
        try await post("/api/apple/navigation/state", body: state)
    }

    public func resumeNavigationHistoryRoute(_ routeID: String) async throws -> NavigationState {
        struct Response: Decodable {
            let state: NavigationState

            enum CodingKeys: String, CodingKey {
                case state = "navigation_state"
            }
        }
        let response: Response = try await post(
            "/api/apple/navigation/history/\(routeID)/resume",
            body: EmptyBody()
        )
        return response.state
    }

    public func fetchNavigationRoute(origin: String, destination: String) async throws -> NavigationRouteOverview {
        let allowed = CharacterSet.urlQueryAllowed
        guard
            let encodedOrigin = origin.addingPercentEncoding(withAllowedCharacters: allowed),
            let encodedDestination = destination.addingPercentEncoding(withAllowedCharacters: allowed)
        else {
            throw JarvisClientError.invalidURL("/api/apple/navigation/route")
        }
        return try await get("/api/apple/navigation/route?origin=\(encodedOrigin)&destination=\(encodedDestination)")
    }

    public func fetchNavigationStops(
        origin: String,
        destination: String,
        parksRadiusMiles: Int = 25
    ) async throws -> NavigationStopsOverview {
        let allowed = CharacterSet.urlQueryAllowed
        guard
            let encodedOrigin = origin.addingPercentEncoding(withAllowedCharacters: allowed),
            let encodedDestination = destination.addingPercentEncoding(withAllowedCharacters: allowed)
        else {
            throw JarvisClientError.invalidURL("/api/apple/navigation/stops")
        }
        return try await get(
            "/api/apple/navigation/stops?origin=\(encodedOrigin)&destination=\(encodedDestination)&parks_radius_miles=\(parksRadiusMiles)"
        )
    }

    @discardableResult
    public func stageCalendarPrep(title: String, start: String = "", location: String = "") async throws -> Bool {
        struct Body: Encodable {
            let title: String
            let start: String
            let location: String
        }
        struct Response: Decodable { let status: String }
        let response: Response = try await post(
            "/api/apple/calendar/stage-prep",
            body: Body(title: title, start: start, location: location)
        )
        return response.status == "staged"
    }

    public func fetchCalendarState() async throws -> CalendarWorkflowOverview {
        try await get("/api/apple/calendar/state")
    }

    public func fetchRemindersState() async throws -> ReminderWorkflowOverview {
        try await get("/api/apple/reminders/state")
    }

    public func fetchFocusState() async throws -> FocusStateOverview {
        try await get("/api/apple/focus-state")
    }

    @discardableResult
    public func applyFocusPreset(
        focusActive: Bool,
        jarvisMode: String,
        holdApprovals: Bool,
        silenceBriefings: Bool,
        source: String = "systems_phone"
    ) async throws -> FocusWorkflowActionResult {
        struct Body: Encodable {
            let focusActive: Bool
            let jarvisMode: String
            let holdApprovals: Bool
            let silenceBriefings: Bool
            let source: String

            enum CodingKeys: String, CodingKey {
                case source
                case focusActive = "focus_active"
                case jarvisMode = "jarvis_mode"
                case holdApprovals = "hold_approvals"
                case silenceBriefings = "silence_briefings"
            }
        }
        let response: FocusWorkflowActionResult = try await post(
            "/api/apple/focus",
            body: Body(
                focusActive: focusActive,
                jarvisMode: jarvisMode,
                holdApprovals: holdApprovals,
                silenceBriefings: silenceBriefings,
                source: source
            )
        )
        return response
    }

    public func fetchSoundHistory() async throws -> SoundHistoryOverview {
        try await get("/api/apple/sound-alerts")
    }

    public func fetchVisionHistory() async throws -> VisionHistoryOverview {
        try await get("/api/apple/vision/scans")
    }

    public func resolveSoundAlert(_ alertId: String) async throws -> SignalResolutionActionResult {
        try await post("/api/apple/sound-alerts/\(alertId)/resolve", body: EmptyBody())
    }

    public func resolveVisionScan(_ scanId: String) async throws -> SignalResolutionActionResult {
        try await post("/api/apple/vision/scans/\(scanId)/resolve", body: EmptyBody())
    }

    public func fetchNowPlayingState() async throws -> NowPlayingStateOverview {
        try await get("/api/apple/now-playing/state")
    }

    public func fetchControlPlaneState() async throws -> ControlPlaneOverview {
        try await get("/api/apple/control-plane/state")
    }

    public func fetchSystemsAdminSummary() async throws -> SystemsAdminSummary {
        let startedAt = Date()
        print("[JARVIS Systems] admin-summary request started base=\(baseURL.absoluteString)")
        do {
            let result: SystemsAdminSummary = try await get("/api/apple/systems/admin-summary")
            print("[JARVIS Systems] admin-summary request finished in \(String(format: "%.3f", Date().timeIntervalSince(startedAt)))s via GET")
            return result
        } catch JarvisClientError.httpError(let code, _) where code == 404 || code == 405 {
            print("[JARVIS Systems] admin-summary GET returned \(code); retrying with POST")
            let result: SystemsAdminSummary = try await post("/api/apple/systems/admin-summary", body: EmptyBody())
            print("[JARVIS Systems] admin-summary request finished in \(String(format: "%.3f", Date().timeIntervalSince(startedAt)))s via POST fallback")
            return result
        } catch {
            print("[JARVIS Systems] admin-summary request failed in \(String(format: "%.3f", Date().timeIntervalSince(startedAt)))s error=\(error.localizedDescription)")
            throw error
        }
    }

    public func fetchSystemsProfileSettings() async throws -> SystemsProfileSettings {
        try await get("/api/apple/systems/profile-settings")
    }

    public func saveSystemsProfileSettings(
        subjectUserId: String = "chris",
        notifications: SystemsProfileNotificationSettings,
        privacy: SystemsProfilePrivacySettings,
        dashboard: SystemsProfileDashboardSettings,
        actor: String = "chris"
    ) async throws -> SystemsProfileSettingsActionResult {
        struct Body: Encodable {
            let actor: String
            let subject_user_id: String
            let notifications: SystemsProfileNotificationSettings
            let privacy: SystemsProfilePrivacySettings
            let dashboard: SystemsProfileDashboardSettings
        }
        return try await post(
            "/api/apple/systems/profile-settings",
            body: Body(
                actor: actor,
                subject_user_id: subjectUserId,
                notifications: notifications,
                privacy: privacy,
                dashboard: dashboard
            )
        )
    }

    public func saveSystemsAccount(
        accountId: String,
        label: String,
        loginHint: String,
        actor: String = "chris"
    ) async throws -> SystemsAccountActionResult {
        struct Body: Encodable {
            let actor: String
            let label: String
            let login_hint: String
        }
        return try await post(
            "/api/apple/systems/accounts/\(accountId)",
            body: Body(actor: actor, label: label, login_hint: loginHint)
        )
    }

    public func saveSystemsConnector(
        accountId: String,
        serviceScope: String,
        status: String,
        notes: String,
        actor: String = "chris"
    ) async throws -> SystemsAccountActionResult {
        struct Body: Encodable {
            let actor: String
            let service_scope: String
            let status: String
            let notes: String
        }
        return try await post(
            "/api/apple/systems/accounts/\(accountId)/connector",
            body: Body(actor: actor, service_scope: serviceScope, status: status, notes: notes)
        )
    }

    public func disconnectSystemsAccount(
        accountId: String,
        actor: String = "chris"
    ) async throws -> SystemsAccountActionResult {
        struct Body: Encodable {
            let actor: String
        }
        return try await post(
            "/api/apple/systems/accounts/\(accountId)/disconnect",
            body: Body(actor: actor)
        )
    }

    public func saveSystemsFamilyMember(
        userId: String,
        role: String,
        permissions: String,
        trustLevel: String,
        preferredTone: String,
        notes: String,
        actor: String = "chris"
    ) async throws -> SystemsFamilyMemberActionResult {
        struct Body: Encodable {
            let actor: String
            let role: String
            let permissions: String
            let trust_level: String
            let preferred_tone: String
            let notes: String
        }
        return try await post(
            "/api/apple/systems/family/\(userId)",
            body: Body(
                actor: actor,
                role: role,
                permissions: permissions,
                trust_level: trustLevel,
                preferred_tone: preferredTone,
                notes: notes
            )
        )
    }

    public func promoteTrustZone(_ zoneId: String, actor: String = "chris", basis: String = "manual promotion from phone") async throws -> SystemsTrustZoneActionResult {
        struct Body: Encodable {
            let actor: String
            let basis: String
        }
        return try await post(
            "/api/apple/systems/trust-zones/\(zoneId)/promote",
            body: Body(actor: actor, basis: basis)
        )
    }

    public func demoteTrustZone(_ zoneId: String, actor: String = "chris", reason: String = "manual demotion from phone") async throws -> SystemsTrustZoneActionResult {
        struct Body: Encodable {
            let actor: String
            let reason: String
        }
        return try await post(
            "/api/apple/systems/trust-zones/\(zoneId)/demote",
            body: Body(actor: actor, reason: reason)
        )
    }

    public func suspendResourceArena(_ arenaId: String, actor: String = "chris", reason: String = "manual suspension from phone") async throws -> SystemsArenaActionResult {
        struct Body: Encodable {
            let actor: String
            let reason: String
        }
        return try await post(
            "/api/apple/systems/resource-arenas/\(arenaId)/suspend",
            body: Body(actor: actor, reason: reason)
        )
    }

    public func resumeResourceArena(_ arenaId: String, actor: String = "chris", reason: String = "manual resume from phone") async throws -> SystemsArenaActionResult {
        struct Body: Encodable {
            let actor: String
            let reason: String
        }
        return try await post(
            "/api/apple/systems/resource-arenas/\(arenaId)/resume",
            body: Body(actor: actor, reason: reason)
        )
    }

    public func executeSandboxJob(_ jobId: String, actor: String = "chris", triggeredBy: String = "apple-systems") async throws -> SystemsSandboxJobActionResult {
        struct Body: Encodable {
            let actor: String
            let triggered_by: String
        }
        return try await post(
            "/api/apple/systems/self-improvement/jobs/\(jobId)/sandbox-execute",
            body: Body(actor: actor, triggered_by: triggeredBy)
        )
    }

    public func cancelSandboxJob(_ jobId: String, actor: String = "chris", reason: String = "manual stop from phone") async throws -> SystemsSandboxJobActionResult {
        struct Body: Encodable {
            let actor: String
            let reason: String
        }
        return try await post(
            "/api/apple/systems/self-improvement/jobs/\(jobId)/sandbox-cancel",
            body: Body(actor: actor, reason: reason)
        )
    }

    public func recoverSandboxJob(_ jobId: String, actor: String = "chris", reason: String = "manual recovery reset from phone") async throws -> SystemsSandboxJobActionResult {
        struct Body: Encodable {
            let actor: String
            let reason: String
        }
        return try await post(
            "/api/apple/systems/self-improvement/jobs/\(jobId)/sandbox-recover",
            body: Body(actor: actor, reason: reason)
        )
    }

    @discardableResult
    public func prepareCalendarEvent(_ eventId: String) async throws -> Bool {
        struct Response: Decodable { let status: String }
        let response: Response = try await post("/api/apple/calendar/events/\(eventId)/prepare", body: EmptyBody())
        return response.status == "staged"
    }

    public func routeCalendarEvent(_ eventId: String) async throws -> CalendarRouteActionResult {
        try await post("/api/apple/calendar/events/\(eventId)/route", body: EmptyBody())
    }

    /// Fetch the Needs You zone items.
    public func fetchNeeds() async throws -> [NeedsItem] {
        try await get("/api/apple/needs")
    }

    public func fetchCarPlayOps() async throws -> CarPlayOpsOverview {
        try await get("/api/apple/carplay/ops")
    }

    public func saveCarPlayOpsFocus(
        module: String,
        route: String,
        reason: String,
        actor: String = "chris"
    ) async throws -> CarPlayProgressFocus {
        struct Body: Encodable {
            let module: String
            let route: String
            let reason: String
            let actor: String
        }
        return try await post(
            "/api/apple/carplay/ops/focus",
            body: Body(module: module, route: route, reason: reason, actor: actor)
        )
    }

    @discardableResult
    public func queueCarPlayAgentRun(
        _ agentId: String,
        actor: String = "chris"
    ) async throws -> Bool {
        struct Body: Encodable { let actor: String }
        struct Response: Decodable { let status: String }
        let response: Response = try await post(
            "/api/apple/carplay/agents/\(agentId)/queue-run",
            body: Body(actor: actor)
        )
        return response.status == "queued"
    }

    @discardableResult
    public func resolveCarPlaySupervision(
        _ requestId: String,
        action: String,
        reason: String = "",
        actor: String = "chris"
    ) async throws -> Bool {
        struct Body: Encodable {
            let reason: String
            let actor: String
        }
        struct Response: Decodable { let status: String }
        let response: Response = try await post(
            "/api/apple/carplay/supervision/\(requestId)/\(action)",
            body: Body(reason: reason, actor: actor)
        )
        return response.status == "approved" || response.status == "rejected"
    }

    public func startCarPlayHuddlePartyMode(actor: String = "chris") async throws -> HuddlePartyModeActionResult {
        struct Body: Encodable { let actor: String }
        return try await post(
            "/api/apple/carplay/huddle/party-mode/start",
            body: Body(actor: actor)
        )
    }

    public func queueCarPlayHuddleIdea(_ ideaId: String, actor: String = "chris") async throws -> HuddleIdeaActionResult {
        struct Body: Encodable { let actor: String }
        return try await post(
            "/api/apple/carplay/huddle/ideas/\(ideaId)/queue",
            body: Body(actor: actor)
        )
    }

    public func passCarPlayHuddleIdea(_ ideaId: String, actor: String = "chris") async throws -> HuddleIdeaActionResult {
        struct Body: Encodable { let actor: String }
        return try await post(
            "/api/apple/carplay/huddle/ideas/\(ideaId)/pass",
            body: Body(actor: actor)
        )
    }

    public func researchCarPlayHuddleIdeaNow(_ ideaId: String, actor: String = "chris") async throws -> HuddleIdeaResearchActionResult {
        struct Body: Encodable { let actor: String }
        return try await post(
            "/api/apple/carplay/huddle/ideas/\(ideaId)/research-now",
            body: Body(actor: actor)
        )
    }

    // MARK: - Voice

    /// Send a text command and receive an agent response.
    ///
    /// - Parameters:
    ///   - text: The command text (from keyboard or Siri dictation).
    ///   - actorId: The actor identifier (default "chris").
    public func speak(text: String, actorId: String = "chris", conversationId: String? = nil) async throws -> SpeakResponse {
        struct Body: Encodable {
            let text: String
            let actor_id: String
            let conversation_id: String?
        }
        return try await post("/api/apple/speak", body: Body(text: text, actor_id: actorId, conversation_id: conversationId))
    }

    /// Fire-and-forget voice command relay from Watch. Ignores response body.
    public func sendVoiceCommand(_ text: String, actor: String = "chris") async throws {
        struct Body: Encodable { let text: String; let actor: String }
        struct Ack: Decodable {}
        let _: Ack = try await post("/api/apple/speak", body: Body(text: text, actor: actor))
    }

    /// Fetch the current voice greeting (for app launch or wake-word).
    public func fetchGreeting(actor: String = "chris") async throws -> VoiceGreeting {
        try await get("/api/apple/voice/greeting?actor=\(actor)")
    }

    /// Fetch the current Apple voice console state, including recent conversation context.
    public func fetchVoiceState(actor: String = "chris", conversationId: String = "") async throws -> VoiceConsoleState {
        let encodedActor = actor.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? actor
        let encodedConversation = conversationId.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? conversationId
        return try await get("/api/apple/voice/state?actor=\(encodedActor)&conversation_id=\(encodedConversation)")
    }

    // MARK: - Health

    /// Fetch the daily health summary for display and Watch complications.
    public func fetchHealthSummary(actor: String = "chris") async throws -> HealthSummary {
        try await get("/api/apple/health/summary?actor=\(actor)")
    }

    public func fetchHealthCheckins(actor: String = "chris") async throws -> HealthCheckInOverview {
        try await get("/api/apple/health/checkins?actor=\(actor)")
    }

    public func submitHealthCheckin(
        symptoms: String,
        note: String,
        energyLevel: Int,
        sleepHours: Double,
        stressLevel: Int,
        actor: String = "chris"
    ) async throws -> HealthCheckInActionResult {
        struct Body: Encodable {
            let actor: String
            let actor_id: String
            let symptoms: String
            let note: String
            let energy_level: Int
            let sleep_hours: Double
            let stress_level: Int
            let source: String
        }
        return try await post(
            "/api/apple/health/checkins",
            body: Body(
                actor: actor,
                actor_id: actor,
                symptoms: symptoms,
                note: note,
                energy_level: energyLevel,
                sleep_hours: sleepHours,
                stress_level: stressLevel,
                source: "iphone-health"
            )
        )
    }

    public func reviewHealthCheckin(
        checkinId: String,
        status: String,
        note: String,
        actor: String = "chris"
    ) async throws -> HealthCheckInActionResult {
        struct Body: Encodable {
            let actor: String
            let status: String
            let note: String
        }
        return try await post(
            "/api/apple/health/checkins/\(checkinId)/review",
            body: Body(actor: actor, status: status, note: note)
        )
    }

    /// Push HealthKit samples from the iPhone to JARVIS for storage and analysis.
    ///
    /// - Returns: The number of samples successfully logged on the server.
    @discardableResult
    public func logHealthSamples(_ samples: [HealthSample], actorId: String = "chris") async throws -> Int {
        struct Body: Encodable {
            let actor_id: String
            let samples: [HealthSample]
        }
        struct LogResult: Decodable {
            let logged: Int
        }
        let result: LogResult = try await post(
            "/api/apple/health/log",
            body: Body(actor_id: actorId, samples: samples)
        )
        return result.logged
    }

    // MARK: - Home

    /// Fetch the current house state for the Home tab.
    public func fetchHomeState() async throws -> HomeState {
        try await get("/api/apple/home/state")
    }

    /// Issue a home command (staged for approval).
    ///
    /// - Returns: An `ApprovalResponse` containing the request ID and status.
    public func sendHomeCommand(_ command: HomeCommand) async throws -> ApprovalResponse {
        try await post("/api/apple/home/command", body: command)
    }

    // MARK: - Device token

    /// Register an APNs device token so the server can send push notifications.
    @discardableResult
    public func registerDeviceToken(
        _ token: String,
        actorId: String = "chris",
        platform: String = "ios"
    ) async -> Bool {
        struct Body: Encodable {
            let actor_id: String
            let token: String
            let platform: String
        }
        struct Result: Decodable { let registered: Bool }
        do {
            let result: Result = try await post(
                "/api/apple/device/register",
                body: Body(actor_id: actorId, token: token, platform: platform)
            )
            return result.registered
        } catch {
            return false
        }
    }

    // MARK: - Approvals

    /// Approve a pending request from the Watch or Phone (one-tap).
    ///
    /// - Returns: `true` when the server confirms approval.
    @discardableResult
    public func approve(requestId: String, approvedBy: String = "chris") async throws -> Bool {
        struct Body: Encodable {
            let approved_by: String
        }
        struct ApproveResult: Decodable {
            let status: String
        }
        let result: ApproveResult = try await post(
            "/api/apple/approvals/\(requestId)/approve",
            body: Body(approved_by: approvedBy)
        )
        return result.status == "approved"
    }

    @discardableResult
    public func reject(requestId: String, reason: String = "", rejectedBy: String = "chris") async throws -> Bool {
        struct Body: Encodable {
            let reason: String
            let rejected_by: String
        }
        struct RejectResult: Decodable {
            let status: String
        }
        let result: RejectResult = try await post(
            "/api/apple/approvals/\(requestId)/reject",
            body: Body(reason: reason, rejected_by: rejectedBy)
        )
        return result.status == "rejected"
    }

    @discardableResult
    public func cancel(requestId: String) async throws -> Bool {
        struct Body: Encodable {}
        struct CancelResult: Decodable {
            let status: String
        }
        let result: CancelResult = try await post(
            "/api/apple/approvals/\(requestId)/cancel",
            body: Body()
        )
        return result.status == "cancelled"
    }

    // MARK: - Presence

    /// Report a presence event (arrived home / left home).
    public func reportPresence(
        actorId: String,
        event: PresenceEvent,
        lat: Double,
        lon: Double
    ) async throws {
        struct Body: Encodable {
            let actor_id: String
            let event: String
            let lat: Double
            let lon: Double
        }
        struct PresenceResult: Decodable {}
        let _: PresenceResult = try await post(
            "/api/apple/presence",
            body: Body(actor_id: actorId, event: event.rawValue, lat: lat, lon: lon)
        )
    }

    // MARK: - Notifications

    // MARK: - Catalyst

    public func fetchCatalyst() async throws -> CatalystOverview {
        try await get("/api/apple/catalyst")
    }

    public func fetchCatalystOps() async throws -> CatalystOpsOverview {
        try await get("/api/apple/catalyst/ops")
    }

    public func saveCatalystProgressFocus(
        module: String,
        route: String,
        reason: String,
        actor: String = "chris"
    ) async throws -> CatalystProgressFocus {
        struct Body: Encodable {
            let module: String
            let route: String
            let reason: String
            let actor: String
        }
        return try await post(
            "/api/apple/catalyst/progress-focus",
            body: Body(module: module, route: route, reason: reason, actor: actor)
        )
    }

    @discardableResult
    public func approveCatalystApproval(_ requestId: String, actor: String = "chris") async throws -> Bool {
        struct Body: Encodable { let actor: String }
        struct Response: Decodable { let status: String }
        let response: Response = try await post(
            "/api/apple/catalyst/approvals/\(requestId)/approve",
            body: Body(actor: actor)
        )
        return response.status == "approved"
    }

    @discardableResult
    public func executeCatalystRecoveryCase(
        _ caseId: String,
        actionType: String,
        note: String = "",
        actor: String = "chris"
    ) async throws -> Bool {
        struct Body: Encodable {
            let action_type: String
            let note: String
            let actor: String
        }
        struct Response: Decodable { let status: String }
        let response: Response = try await post(
            "/api/apple/catalyst/recovery-cases/\(caseId)/execute",
            body: Body(action_type: actionType, note: note, actor: actor)
        )
        return response.status == "recorded"
    }

    @discardableResult
    public func remediateCatalystRecoveryCase(
        _ caseId: String,
        actionType: String,
        note: String = "",
        actor: String = "chris"
    ) async throws -> Bool {
        struct Body: Encodable {
            let action_type: String
            let note: String
            let actor: String
        }
        struct Response: Decodable { let status: String }
        let response: Response = try await post(
            "/api/apple/catalyst/recovery-cases/\(caseId)/remediation",
            body: Body(action_type: actionType, note: note, actor: actor)
        )
        return response.status == "recorded"
    }

    @discardableResult
    public func executeNextCatalystRecoveryPlanStep(
        _ caseId: String,
        note: String = "",
        actor: String = "chris"
    ) async throws -> Bool {
        struct Body: Encodable {
            let note: String
            let actor: String
        }
        struct Response: Decodable { let status: String }
        let response: Response = try await post(
            "/api/apple/catalyst/recovery-cases/\(caseId)/plan/execute-next",
            body: Body(note: note, actor: actor)
        )
        return response.status == "recorded"
    }

    @discardableResult
    public func queueCatalystAgentRun(
        _ agentId: String,
        actor: String = "chris"
    ) async throws -> Bool {
        struct Body: Encodable { let actor: String }
        struct Response: Decodable { let status: String }
        let response: Response = try await post(
            "/api/apple/catalyst/agents/\(agentId)/queue-run",
            body: Body(actor: actor)
        )
        return response.status == "queued"
    }

    public func saveCatalystAgentAssignment(
        _ agentId: String,
        missionId: String,
        policyAssignment: String = "",
        purpose: String = "",
        actor: String = "chris"
    ) async throws -> CatalystAgentAssignmentResult {
        struct Body: Encodable {
            let mission_id: String
            let policy_assignment: String
            let purpose: String
            let actor: String
        }
        return try await post(
            "/api/apple/catalyst/agents/\(agentId)/assignment",
            body: Body(
                mission_id: missionId,
                policy_assignment: policyAssignment,
                purpose: purpose,
                actor: actor
            )
        )
    }

    @discardableResult
    public func resolveCatalystSupervision(
        _ requestId: String,
        action: String,
        reason: String = "",
        actor: String = "chris"
    ) async throws -> Bool {
        struct Body: Encodable {
            let reason: String
            let actor: String
        }
        struct Response: Decodable { let status: String }
        let response: Response = try await post(
            "/api/apple/catalyst/supervision/\(requestId)/\(action)",
            body: Body(reason: reason, actor: actor)
        )
        return response.status == "approved" || response.status == "rejected"
    }

    @discardableResult
    public func updateCatalystMissionStatus(
        _ missionId: String,
        status: String,
        note: String = "",
        actor: String = "chris"
    ) async throws -> Bool {
        struct Body: Encodable {
            let status: String
            let note: String
            let actor: String
        }
        struct Response: Decodable { let status: String }
        let response: Response = try await post(
            "/api/apple/catalyst/missions/\(missionId)/status",
            body: Body(status: status, note: note, actor: actor)
        )
        return response.status == "recorded"
    }

    // MARK: - Chronicle

    public func fetchChronicle() async throws -> ChronicleOverview {
        try await get("/api/apple/chronicle")
    }

    @discardableResult
    public func captureChronicle(_ capture: ChronicleCapture) async throws -> ChronicleCaptureResult {
        try await post("/api/apple/chronicle/capture", body: capture)
    }

    public func markChroniclePrayerPrayed(_ prayerId: String, payload: ChroniclePrayerActionPayload) async throws -> ChroniclePrayerActionResult {
        try await post("/api/apple/chronicle/prayers/\(prayerId)/pray", body: payload)
    }

    public func markChroniclePrayerAnswered(_ prayerId: String, payload: ChroniclePrayerActionPayload) async throws -> ChroniclePrayerActionResult {
        try await post("/api/apple/chronicle/prayers/\(prayerId)/answer", body: payload)
    }

    public func saveChronicleStudy(_ payload: ChronicleStudySavePayload) async throws -> ChronicleStudySaveResult {
        try await post("/api/apple/chronicle/study/save", body: payload)
    }

    public func reviewChronicleEntry(_ entryId: String, payload: ChronicleReviewPayload) async throws -> ChronicleReviewResult {
        try await post("/api/apple/chronicle/entries/\(entryId)/review", body: payload)
    }

    // MARK: - Faith

    public func fetchFaith(actor: String = "chris") async throws -> FaithOverview {
        try await get("/api/apple/faith?actor=\(actor)")
    }

    public func chatFaith(_ payload: FaithChatPayload) async throws -> FaithChatResponse {
        try await post("/api/apple/faith/chat", body: payload)
    }

    // MARK: - Publishing

    public func fetchPublishing() async throws -> PublishOverview {
        try await get("/api/apple/publishing")
    }

    public func approvePublishingReview(_ reviewId: String) async throws -> PublishReviewActionResult {
        struct Body: Encodable {}
        return try await post("/api/apple/publishing/reviews/\(reviewId)/approve", body: Body())
    }

    public func requestPublishingRevision(_ reviewId: String, feedback: String = "Needs revision from JarvisPhone.") async throws -> PublishReviewActionResult {
        struct Body: Encodable { let feedback: String }
        return try await post(
            "/api/apple/publishing/reviews/\(reviewId)/revise",
            body: Body(feedback: feedback)
        )
    }

    public func updatePublishingChecklistStep(
        projectId: String,
        step: String,
        completed: Bool,
        actor: String = "chris"
    ) async throws -> PublishChecklistActionResult {
        struct Body: Encodable {
            let completed: Bool
            let actor: String
        }
        return try await post(
            "/api/apple/publishing/checklist/\(projectId)/\(step)",
            body: Body(completed: completed, actor: actor)
        )
    }

    // MARK: - Huddle

    public func fetchHuddle() async throws -> HuddleOverview {
        try await get("/api/apple/huddle")
    }

    public func startHuddlePartyMode() async throws -> HuddlePartyModeActionResult {
        try await post("/api/apple/huddle/party-mode/start", body: EmptyBody())
    }

    public func approveHuddleDecision(_ workId: String, actor: String = "chris", note: String = "") async throws -> HuddleApprovalActionResult {
        struct Body: Encodable {
            let actor: String
            let note: String
        }
        return try await post(
            "/api/apple/huddle/approvals/\(workId)/approve",
            body: Body(actor: actor, note: note)
        )
    }

    public func rejectHuddleDecision(_ workId: String, actor: String = "chris", note: String = "") async throws -> HuddleApprovalActionResult {
        struct Body: Encodable {
            let actor: String
            let note: String
        }
        return try await post(
            "/api/apple/huddle/approvals/\(workId)/reject",
            body: Body(actor: actor, note: note)
        )
    }

    public func captureHuddleIdea(
        text: String,
        domain: String = "passive-income",
        notes: String = "",
        actor: String = "chris"
    ) async throws -> HuddleIdeaActionResult {
        struct Body: Encodable {
            let actor: String
            let text: String
            let domain: String
            let notes: String
        }
        return try await post(
            "/api/apple/huddle/ideas",
            body: Body(actor: actor, text: text, domain: domain, notes: notes)
        )
    }

    public func queueHuddleIdea(_ ideaId: String, actor: String = "chris") async throws -> HuddleIdeaActionResult {
        struct Body: Encodable {
            let actor: String
        }
        return try await post(
            "/api/apple/huddle/ideas/\(ideaId)/queue",
            body: Body(actor: actor)
        )
    }

    public func passHuddleIdea(_ ideaId: String, actor: String = "chris") async throws -> HuddleIdeaActionResult {
        struct Body: Encodable {
            let actor: String
        }
        return try await post(
            "/api/apple/huddle/ideas/\(ideaId)/pass",
            body: Body(actor: actor)
        )
    }

    public func researchHuddleIdeaNow(_ ideaId: String, actor: String = "chris") async throws -> HuddleIdeaResearchActionResult {
        struct Body: Encodable {
            let actor: String
        }
        return try await post(
            "/api/apple/huddle/ideas/\(ideaId)/research-now",
            body: Body(actor: actor)
        )
    }

    public func stageStewardshipLaneReview(_ laneId: String, actor: String = "chris", note: String = "") async throws -> StewardshipLaneActionResult {
        struct Body: Encodable {
            let actor: String
            let note: String
        }
        return try await post(
            "/api/apple/stewardship-lanes/\(laneId)/stage-review",
            body: Body(actor: actor, note: note)
        )
    }

    public func approveStewardshipReview(_ reviewId: String, actor: String = "chris") async throws -> StewardshipLaneActionResult {
        struct Body: Encodable {
            let actor: String
        }
        return try await post(
            "/api/apple/stewardship-reviews/\(reviewId)/approve",
            body: Body(actor: actor)
        )
    }

    public func routeStewardshipReview(
        _ reviewId: String,
        reviewSurface: String,
        packetTarget: String,
        actor: String = "chris"
    ) async throws -> StewardshipLaneActionResult {
        struct Body: Encodable {
            let actor: String
            let reviewSurface: String
            let packetTarget: String

            enum CodingKeys: String, CodingKey {
                case actor
                case reviewSurface = "review_surface"
                case packetTarget = "packet_target"
            }
        }
        return try await post(
            "/api/apple/stewardship-reviews/\(reviewId)/route",
            body: Body(actor: actor, reviewSurface: reviewSurface, packetTarget: packetTarget)
        )
    }

    public func retireStewardshipReview(
        _ reviewId: String,
        actor: String = "chris",
        reason: String = "Retired from Systems/Admin."
    ) async throws -> StewardshipLaneActionResult {
        struct Body: Encodable {
            let actor: String
            let reason: String
        }
        return try await post(
            "/api/apple/stewardship-reviews/\(reviewId)/retire",
            body: Body(actor: actor, reason: reason)
        )
    }

    public func promoteGovernanceProposal(
        _ proposalId: String,
        actor: String = "chris",
        basis: String = "Promoted from Systems/Admin."
    ) async throws -> GovernanceProposalActionResult {
        struct Body: Encodable {
            let actor: String
            let basis: String
        }
        return try await post(
            "/api/apple/governance-proposals/\(proposalId)/promote",
            body: Body(actor: actor, basis: basis)
        )
    }

    public func dismissGovernanceProposal(
        _ proposalId: String,
        actor: String = "chris",
        reason: String = "Dismissed from Systems/Admin."
    ) async throws -> GovernanceProposalActionResult {
        struct Body: Encodable {
            let actor: String
            let reason: String
        }
        return try await post(
            "/api/apple/governance-proposals/\(proposalId)/dismiss",
            body: Body(actor: actor, reason: reason)
        )
    }

    // MARK: - Forge

    public func fetchForgeOverview() async throws -> ForgeOverview {
        try await get("/api/apple/forge")
    }

    public func fetchForgeModels() async throws -> [ForgeModelRecord] {
        struct Wrapper: Decodable { let models: [ForgeModelRecord] }
        let w: Wrapper = try await get("/api/apple/forge")
        return w.models
    }

    public func createForgeProject(_ payload: ForgeProjectCreatePayload) async throws -> ForgeProjectDetail {
        try await post("/api/apple/forge/projects", body: payload)
    }

    @discardableResult
    public func saveForgeModel(_ model: ForgeModelRecord) async throws -> Bool {
        struct Result: Decodable { let saved: Bool }
        let r: Result = try await post("/api/apple/forge/save", body: model)
        return r.saved
    }

    /// Submit captured photos to JARVIS for server-side photogrammetry.
    public func submitForgeJob(_ job: ForgeJobPayload) async throws -> ForgeJobResult {
        try await post("/api/apple/forge/submit", body: job)
    }

    // MARK: - Generic acknowledgements

    /// POST an Encodable payload to an Apple endpoint that only needs the standard
    /// `{ "ok": ... }` envelope checked. Useful for fire-and-forget device signals.
    public func postAcknowledged<B: Encodable & Sendable>(_ path: String, body: B) async throws {
        guard let url = URL(string: path, relativeTo: baseURL) else {
            throw JarvisClientError.invalidURL(path)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.httpBody = try JSONEncoder().encode(body)
        try await performEnvelopeOnly(request)
    }

    // MARK: - Notifications

    /// Pull pending server-side notifications and clear them.
    public func fetchPendingNotifications() async throws -> [PendingNotification] {
        struct NotificationsWrapper: Decodable {
            let notifications: [PendingNotification]
        }
        let wrapper: NotificationsWrapper = try await get("/api/apple/notifications/pending")
        return wrapper.notifications
    }

    public func fetchNotificationCenterOverview(status: String = "", limit: Int = 50) async throws -> NotificationCenterOverview {
        let safeStatus = status.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        return try await get("/api/apple/notifications?status=\(safeStatus)&limit=\(limit)")
    }

    public func fetchNotifications(status: String = "", limit: Int = 50) async throws -> [NotificationCenterItem] {
        try await fetchNotificationCenterOverview(status: status, limit: limit).notifications
    }

    public func fetchRecentEvents(limit: Int = 25) async throws -> [EventTimelineItem] {
        let wrapper: EventTimelineOverview = try await get("/api/apple/events/recent?limit=\(limit)")
        return wrapper.events
    }

    @discardableResult
    public func markNotificationSeen(_ notificationId: String) async throws -> Bool {
        struct Response: Decodable { let status: String }
        let response: Response = try await post("/api/apple/notifications/\(notificationId)/seen", body: EmptyBody())
        return response.status == "seen"
    }

    @discardableResult
    public func dismissNotification(_ notificationId: String) async throws -> Bool {
        struct Response: Decodable { let status: String }
        let response: Response = try await post("/api/apple/notifications/\(notificationId)/dismiss", body: EmptyBody())
        return response.status == "dismissed"
    }

    public func resolveNotification(_ notificationId: String) async throws -> NotificationWorkflowActionResult {
        try await post("/api/apple/notifications/\(notificationId)/resolve", body: EmptyBody())
    }

    public func snoozeNotification(_ notificationId: String) async throws -> NotificationWorkflowActionResult {
        try await post("/api/apple/notifications/\(notificationId)/snooze", body: EmptyBody())
    }

    @discardableResult
    public func performNotificationAction(_ notificationId: String, action: String) async throws -> Bool {
        struct Body: Encodable { let action: String }
        struct Response: Decodable {
            let ok: Bool?
            let status: String?
            let performedAction: String?

            enum CodingKeys: String, CodingKey {
                case ok, status
                case performedAction = "performed_action"
            }
        }
        let response: Response = try await post("/api/apple/notifications/\(notificationId)/action", body: Body(action: action))
        return response.ok ?? !(response.status ?? "").isEmpty || response.performedAction == action
    }

    public func completeReminder(_ reminderId: String) async throws -> ReminderWorkflowActionResult {
        try await post("/api/apple/reminders/\(reminderId)/complete", body: EmptyBody())
    }

    public func snoozeReminder(_ reminderId: String, minutes: Int = 60) async throws -> ReminderWorkflowActionResult {
        struct Body: Encodable { let minutes: Int }
        return try await post("/api/apple/reminders/\(reminderId)/snooze", body: Body(minutes: minutes))
    }

    // MARK: - Internal networking

    private func get<T: Decodable>(_ path: String) async throws -> T {
        guard let url = URL(string: path, relativeTo: baseURL) else {
            throw JarvisClientError.invalidURL(path)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        return try await perform(request)
    }

    private func post<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T {
        guard let url = URL(string: path, relativeTo: baseURL) else {
            throw JarvisClientError.invalidURL(path)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.httpBody = try JSONEncoder().encode(body)
        return try await perform(request)
    }

    private func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        var request = request
        JARVISAccessConfig.apply(to: &request)
        let (data, response) = try await URLSession.shared.data(for: request)

        guard let http = response as? HTTPURLResponse else {
            throw JarvisClientError.invalidResponse
        }

        guard (200..<300).contains(http.statusCode) else {
            let message = String(data: data, encoding: .utf8) ?? "HTTP \(http.statusCode)"
            throw JarvisClientError.httpError(http.statusCode, message)
        }

        // Unwrap the standard JARVIS envelope {"ok": bool, "data": ..., "error": ...}
        let envelope = try JSONDecoder().decode(APIEnvelope<T>.self, from: data)

        if !envelope.ok {
            throw JarvisClientError.serverError(envelope.error ?? "Unknown server error")
        }

        guard let result = envelope.data else {
            throw JarvisClientError.missingData
        }
        return result
    }

    private func performEnvelopeOnly(_ request: URLRequest) async throws {
        var request = request
        JARVISAccessConfig.apply(to: &request)
        let (data, response) = try await URLSession.shared.data(for: request)

        guard let http = response as? HTTPURLResponse else {
            throw JarvisClientError.invalidResponse
        }

        guard (200..<300).contains(http.statusCode) else {
            let message = String(data: data, encoding: .utf8) ?? "HTTP \(http.statusCode)"
            throw JarvisClientError.httpError(http.statusCode, message)
        }

        let envelope = try JSONDecoder().decode(APIAckEnvelope.self, from: data)
        if !envelope.ok {
            throw JarvisClientError.serverError(envelope.error ?? "Unknown server error")
        }
    }

    // MARK: - Envelope

    private struct APIEnvelope<T: Decodable>: Decodable {
        let ok: Bool
        let data: T?
        let error: String?
    }

    private struct APIAckEnvelope: Decodable {
        let ok: Bool
        let error: String?
    }

    private struct EmptyBody: Encodable {}
}

// MARK: - PendingNotification

/// A notification queued on the server for APNs delivery.
public struct PendingNotification: Codable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let body: String
    public let category: String
    public let badge: Int
    public let createdAt: String?

    enum CodingKeys: String, CodingKey {
        case id, title, body, category, badge
        case createdAt = "created_at"
    }
}

// MARK: - JarvisClientError

public enum JarvisClientError: Error, LocalizedError, Sendable {
    case invalidURL(String)
    case invalidResponse
    case httpError(Int, String)
    case serverError(String)
    case missingData

    public var errorDescription: String? {
        switch self {
        case .invalidURL(let path):
            return "Invalid URL: \(path)"
        case .invalidResponse:
            return "Invalid server response"
        case .httpError(let code, let message):
            if code == 502 || code == 503 || code == 504 {
                return "JARVIS is restarting or Cloudflare cannot reach the server. Please retry in a moment."
            }
            if code == 403 {
                return "Cloudflare Access denied this request. Check the app access credentials."
            }
            let clean = message
                .replacingOccurrences(of: "\n", with: " ")
                .replacingOccurrences(of: "\t", with: " ")
            return "HTTP \(code): \(String(clean.prefix(180)))"
        case .serverError(let message):
            return "Server error: \(message)"
        case .missingData:
            return "Response envelope contained no data"
        }
    }
}
