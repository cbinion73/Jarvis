import Foundation
import Testing
@testable import JarvisKit

struct ApplePayloadDecodingTests {
    @Test
    func decodesMinimalSpeakResponseUsingFallbackFields() throws {
        let json = """
        {
          "response": "Schedule summary",
          "agent": "JARVIS",
          "speak": true
        }
        """.data(using: .utf8)!

        let decoded = try JSONDecoder().decode(SpeakResponse.self, from: json)
        #expect(decoded.response == "Schedule summary")
        #expect(decoded.displayText == "Schedule summary")
        #expect(decoded.spokenText == "Schedule summary")
        #expect(decoded.presentationMode == "spoken_reply")
    }

    @Test
    func decodesSystemsAdminStewardshipReviewWithoutSandboxJobId() throws {
        let json = """
        {
          "id": "stewardship-review-1",
          "lane_id": "family-stewardship",
          "lane_title": "Family Stewardship",
          "status": "review_staged",
          "review_surface": "home",
          "packet_target": "family",
          "boundary_decision": "stage",
          "boundary_reason": "The family lane is still gated for reviewed household changes.",
          "approval_mode": "stage_and_alert",
          "timestamp": "2026-06-01T08:28:00Z"
        }
        """.data(using: .utf8)!

        let decoded = try JSONDecoder().decode(SystemsAdminStewardshipReviewItem.self, from: json)
        #expect(decoded.id == "stewardship-review-1")
        #expect(decoded.sandboxJobId.isEmpty)
    }

    @Test
    func decodesLiveApplePayloadFixtureWhenProvided() throws {
        guard let fixturePath = ProcessInfo.processInfo.environment["JARVIS_APPLE_PAYLOAD_FIXTURE"] else {
            return
        }

        let data = try Data(contentsOf: URL(fileURLWithPath: fixturePath))
        let payloads = try JSONDecoder().decode([String: JSONValue].self, from: data)
        let decoder = JSONDecoder()

        try decode(WatchStatus.self, from: payloads, key: "/api/apple/status", decoder: decoder)
        try decode(AppStateOverview.self, from: payloads, key: "/api/apple/app-state", decoder: decoder)
        try decode(CalendarWorkflowOverview.self, from: payloads, key: "/api/apple/calendar/state", decoder: decoder)
        try decode(ReminderWorkflowOverview.self, from: payloads, key: "/api/apple/reminders/state", decoder: decoder)
        try decode(FocusStateOverview.self, from: payloads, key: "/api/apple/focus-state", decoder: decoder)
        try decode(SoundHistoryOverview.self, from: payloads, key: "/api/apple/sound-alerts", decoder: decoder)
        try decode(VisionHistoryOverview.self, from: payloads, key: "/api/apple/vision/scans", decoder: decoder)
        try decode(NowPlayingStateOverview.self, from: payloads, key: "/api/apple/now-playing/state", decoder: decoder)
        try decode(ControlPlaneOverview.self, from: payloads, key: "/api/apple/control-plane/state", decoder: decoder)
        try decode(SystemsAdminSummary.self, from: payloads, key: "/api/apple/systems/admin-summary", decoder: decoder)
        try decode(SystemsProfileSettings.self, from: payloads, key: "/api/apple/systems/profile-settings", decoder: decoder)
        try decode(NotificationCenterOverview.self, from: payloads, key: "/api/apple/notifications", decoder: decoder)
        try decode(EventTimelineOverview.self, from: payloads, key: "/api/apple/events/recent", decoder: decoder)
        try decode(AppleWeatherOverview.self, from: payloads, key: "/api/apple/weather", decoder: decoder)
        try decode(NavigationLocationsOverview.self, from: payloads, key: "/api/apple/navigation/locations", decoder: decoder)
        try decode(CarPlayOpsOverview.self, from: payloads, key: "/api/apple/carplay/ops", decoder: decoder)
        try decode(
            NavigationRouteOverview.self,
            from: payloads,
            key: "/api/apple/navigation/route?origin=8384%20Riley%20Rd%2C%20Alexandria%2C%20KY%2041001&destination=Cincinnati%2C%20OH",
            decoder: decoder
        )
        try decode(BriefingPacket.self, from: payloads, key: "/api/apple/briefing?actor=chris", decoder: decoder)
        try decode(BriefingOpenLoopActionResult.self, from: payloads, key: "/api/apple/briefing/open-loops/loop-1/action", decoder: decoder)
        try decode([NeedsItem].self, from: payloads, key: "/api/apple/needs", decoder: decoder)
        try decode(HealthSummary.self, from: payloads, key: "/api/apple/health/summary?actor=chris", decoder: decoder)
        try decode(HomeState.self, from: payloads, key: "/api/apple/home/state", decoder: decoder)
        try decode(CatalystOverview.self, from: payloads, key: "/api/apple/catalyst", decoder: decoder)
        try decode(CatalystOpsOverview.self, from: payloads, key: "/api/apple/catalyst/ops", decoder: decoder)
        try decode(ChronicleOverview.self, from: payloads, key: "/api/apple/chronicle", decoder: decoder)
        try decode(FaithOverview.self, from: payloads, key: "/api/apple/faith?actor=chris", decoder: decoder)
        try decode(PublishOverview.self, from: payloads, key: "/api/apple/publishing", decoder: decoder)
        try decode(PublishChecklistActionResult.self, from: payloads, key: "/api/apple/publishing/checklist/pub-1/pricing_set", decoder: decoder)
        try decode(HuddleOverview.self, from: payloads, key: "/api/apple/huddle", decoder: decoder)
        try decode(HuddleIdeaActionResult.self, from: payloads, key: "/api/apple/huddle/ideas", decoder: decoder)
        try decode(HuddleIdeaActionResult.self, from: payloads, key: "/api/apple/huddle/ideas/idea-1/queue", decoder: decoder)
        try decode(HuddleIdeaActionResult.self, from: payloads, key: "/api/apple/huddle/ideas/idea-1/pass", decoder: decoder)
        try decode(HuddleIdeaResearchActionResult.self, from: payloads, key: "/api/apple/huddle/ideas/idea-1/research-now", decoder: decoder)
        try decode(HuddlePartyModeActionResult.self, from: payloads, key: "/api/apple/carplay/huddle/party-mode/start", decoder: decoder)
        try decode(HuddleIdeaActionResult.self, from: payloads, key: "/api/apple/carplay/huddle/ideas/idea-1/queue", decoder: decoder)
        try decode(HuddleIdeaActionResult.self, from: payloads, key: "/api/apple/carplay/huddle/ideas/idea-1/pass", decoder: decoder)
        try decode(HuddleIdeaResearchActionResult.self, from: payloads, key: "/api/apple/carplay/huddle/ideas/idea-1/research-now", decoder: decoder)
        try decode(ForgeWrapper.self, from: payloads, key: "/api/apple/forge", decoder: decoder)
    }

    private struct Envelope<T: Decodable>: Decodable {
        let ok: Bool
        let data: T
    }

    private struct ForgeWrapper: Decodable {
        let models: [ForgeModelRecord]
    }

    private func decode<T: Decodable>(
        _ type: T.Type,
        from payloads: [String: JSONValue],
        key: String,
        decoder: JSONDecoder
    ) throws {
        let value = try #require(payloads[key])
        let data = try JSONEncoder().encode(value)
        _ = try decoder.decode(Envelope<T>.self, from: data)
    }
}

private enum JSONValue: Codable {
    case object([String: JSONValue])
    case array([JSONValue])
    case string(String)
    case number(Double)
    case bool(Bool)
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Double.self) {
            self = .number(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([String: JSONValue].self) {
            self = .object(value)
        } else {
            self = .array(try container.decode([JSONValue].self))
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .object(let value):
            try container.encode(value)
        case .array(let value):
            try container.encode(value)
        case .string(let value):
            try container.encode(value)
        case .number(let value):
            try container.encode(value)
        case .bool(let value):
            try container.encode(value)
        case .null:
            try container.encodeNil()
        }
    }
}
