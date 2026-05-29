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

    public func fetchSoundHistory() async throws -> SoundHistoryOverview {
        try await get("/api/apple/sound-alerts")
    }

    public func fetchVisionHistory() async throws -> VisionHistoryOverview {
        try await get("/api/apple/vision/scans")
    }

    @discardableResult
    public func resolveSoundAlert(_ alertId: String) async throws -> Bool {
        struct Response: Decodable { let status: String }
        let response: Response = try await post("/api/apple/sound-alerts/\(alertId)/resolve", body: EmptyBody())
        return response.status == "resolved"
    }

    @discardableResult
    public func resolveVisionScan(_ scanId: String) async throws -> Bool {
        struct Response: Decodable { let status: String }
        let response: Response = try await post("/api/apple/vision/scans/\(scanId)/resolve", body: EmptyBody())
        return response.status == "resolved"
    }

    public func fetchNowPlayingState() async throws -> NowPlayingStateOverview {
        try await get("/api/apple/now-playing/state")
    }

    public func fetchControlPlaneState() async throws -> ControlPlaneOverview {
        try await get("/api/apple/control-plane/state")
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

    // MARK: - Voice

    /// Send a text command and receive an agent response.
    ///
    /// - Parameters:
    ///   - text: The command text (from keyboard or Siri dictation).
    ///   - actorId: The actor identifier (default "chris").
    public func speak(text: String, actorId: String = "chris") async throws -> SpeakResponse {
        struct Body: Encodable {
            let text: String
            let actor_id: String
        }
        return try await post("/api/apple/speak", body: Body(text: text, actor_id: actorId))
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

    // MARK: - Health

    /// Fetch the daily health summary for display and Watch complications.
    public func fetchHealthSummary(actor: String = "chris") async throws -> HealthSummary {
        try await get("/api/apple/health/summary?actor=\(actor)")
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

    // MARK: - Chronicle

    public func fetchChronicle() async throws -> ChronicleOverview {
        try await get("/api/apple/chronicle")
    }

    @discardableResult
    public func captureChronicle(_ capture: ChronicleCapture) async throws -> Bool {
        struct Result: Decodable { let captured: Bool }
        let r: Result = try await post("/api/apple/chronicle/capture", body: capture)
        return r.captured
    }

    // MARK: - Faith

    public func fetchFaith(actor: String = "chris") async throws -> FaithOverview {
        try await get("/api/apple/faith?actor=\(actor)")
    }

    // MARK: - Publishing

    public func fetchPublishing() async throws -> PublishOverview {
        try await get("/api/apple/publishing")
    }

    @discardableResult
    public func approvePublishingReview(_ reviewId: String) async throws -> Bool {
        struct Body: Encodable {}
        struct Result: Decodable { let status: String }
        let result: Result = try await post("/api/apple/publishing/reviews/\(reviewId)/approve", body: Body())
        return result.status == "approved"
    }

    @discardableResult
    public func requestPublishingRevision(_ reviewId: String, feedback: String = "Needs revision from JarvisPhone.") async throws -> Bool {
        struct Body: Encodable { let feedback: String }
        struct Result: Decodable { let status: String }
        let result: Result = try await post(
            "/api/apple/publishing/reviews/\(reviewId)/revise",
            body: Body(feedback: feedback)
        )
        return result.status == "needs_revision"
    }

    // MARK: - Huddle

    public func fetchHuddle() async throws -> HuddleOverview {
        try await get("/api/apple/huddle")
    }

    // MARK: - Forge

    public func fetchForgeModels() async throws -> [ForgeModelRecord] {
        struct Wrapper: Decodable { let models: [ForgeModelRecord] }
        let w: Wrapper = try await get("/api/apple/forge")
        return w.models
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

    public func fetchNotifications(status: String = "", limit: Int = 50) async throws -> [NotificationCenterItem] {
        let safeStatus = status.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        let wrapper: NotificationCenterOverview = try await get("/api/apple/notifications?status=\(safeStatus)&limit=\(limit)")
        return wrapper.notifications
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

    @discardableResult
    public func resolveNotification(_ notificationId: String) async throws -> Bool {
        struct Response: Decodable { let status: String }
        let response: Response = try await post("/api/apple/notifications/\(notificationId)/resolve", body: EmptyBody())
        return response.status == "resolved"
    }

    @discardableResult
    public func snoozeNotification(_ notificationId: String) async throws -> Bool {
        struct Response: Decodable { let status: String }
        let response: Response = try await post("/api/apple/notifications/\(notificationId)/snooze", body: EmptyBody())
        return response.status == "snoozed"
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

    @discardableResult
    public func completeReminder(_ reminderId: String) async throws -> Bool {
        struct Response: Decodable { let status: String }
        let response: Response = try await post("/api/apple/reminders/\(reminderId)/complete", body: EmptyBody())
        return response.status == "completed"
    }

    @discardableResult
    public func snoozeReminder(_ reminderId: String, minutes: Int = 60) async throws -> Bool {
        struct Body: Encodable { let minutes: Int }
        struct Response: Decodable { let status: String }
        let response: Response = try await post("/api/apple/reminders/\(reminderId)/snooze", body: Body(minutes: minutes))
        return response.status == "snoozed"
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
        request.setValue(CloudflareConfig.clientId,     forHTTPHeaderField: "CF-Access-Client-Id")
        request.setValue(CloudflareConfig.clientSecret, forHTTPHeaderField: "CF-Access-Client-Secret")
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
        request.setValue(CloudflareConfig.clientId,     forHTTPHeaderField: "CF-Access-Client-Id")
        request.setValue(CloudflareConfig.clientSecret, forHTTPHeaderField: "CF-Access-Client-Secret")
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
