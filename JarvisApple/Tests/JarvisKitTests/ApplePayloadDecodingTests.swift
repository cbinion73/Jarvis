import Foundation
import Testing
@testable import JarvisKit

struct ApplePayloadDecodingTests {
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
        try decode(NotificationCenterOverview.self, from: payloads, key: "/api/apple/notifications", decoder: decoder)
        try decode(EventTimelineOverview.self, from: payloads, key: "/api/apple/events/recent", decoder: decoder)
        try decode(AppleWeatherOverview.self, from: payloads, key: "/api/apple/weather", decoder: decoder)
        try decode(NavigationLocationsOverview.self, from: payloads, key: "/api/apple/navigation/locations", decoder: decoder)
        try decode(
            NavigationRouteOverview.self,
            from: payloads,
            key: "/api/apple/navigation/route?origin=8384%20Riley%20Rd%2C%20Alexandria%2C%20KY%2041001&destination=Cincinnati%2C%20OH",
            decoder: decoder
        )
        try decode(BriefingPacket.self, from: payloads, key: "/api/apple/briefing?actor=chris", decoder: decoder)
        try decode([NeedsItem].self, from: payloads, key: "/api/apple/needs", decoder: decoder)
        try decode(HealthSummary.self, from: payloads, key: "/api/apple/health/summary?actor=chris", decoder: decoder)
        try decode(HomeState.self, from: payloads, key: "/api/apple/home/state", decoder: decoder)
        try decode(CatalystOverview.self, from: payloads, key: "/api/apple/catalyst", decoder: decoder)
        try decode(ChronicleOverview.self, from: payloads, key: "/api/apple/chronicle", decoder: decoder)
        try decode(FaithOverview.self, from: payloads, key: "/api/apple/faith?actor=chris", decoder: decoder)
        try decode(PublishOverview.self, from: payloads, key: "/api/apple/publishing", decoder: decoder)
        try decode(HuddleOverview.self, from: payloads, key: "/api/apple/huddle", decoder: decoder)
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
