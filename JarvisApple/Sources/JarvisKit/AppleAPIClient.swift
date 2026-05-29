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
            return "HTTP \(code): \(message)"
        case .serverError(let message):
            return "Server error: \(message)"
        case .missingData:
            return "Response envelope contained no data"
        }
    }
}
