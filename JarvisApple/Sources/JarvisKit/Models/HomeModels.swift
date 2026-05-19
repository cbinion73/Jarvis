import Foundation

// MARK: - HomeState

/// Full house state returned by GET /api/apple/home/state
public struct HomeState: Codable, Sendable {
    public let presentMembers: [String]
    public let doors: [String: String]
    public let temperature: TemperatureState
    public let lightsOn: [String]
    public let alerts: [HomeAlert]

    public init(
        presentMembers: [String],
        doors: [String: String],
        temperature: TemperatureState,
        lightsOn: [String],
        alerts: [HomeAlert]
    ) {
        self.presentMembers = presentMembers
        self.doors = doors
        self.temperature = temperature
        self.lightsOn = lightsOn
        self.alerts = alerts
    }

    enum CodingKeys: String, CodingKey {
        case presentMembers = "present_members"
        case doors
        case temperature
        case lightsOn = "lights_on"
        case alerts
    }
}

// MARK: - TemperatureState

public struct TemperatureState: Codable, Sendable {
    public let inside: Double
    public let target: Double
    /// "cool" | "heat" | "auto" | "off"
    public let mode: String

    public init(inside: Double, target: Double, mode: String) {
        self.inside = inside
        self.target = target
        self.mode = mode
    }
}

// MARK: - HomeAlert

public struct HomeAlert: Codable, Sendable {
    public let entity: String
    public let state: String
    public let message: String

    public init(entity: String, state: String, message: String) {
        self.entity = entity
        self.state = state
        self.message = message
    }
}

// MARK: - HomeCommand

/// Command body for POST /api/apple/home/command
public struct HomeCommand: Codable, Sendable {
    public let command: String
    public let entityId: String
    public let service: String

    public init(command: String, entityId: String, service: String) {
        self.command = command
        self.entityId = entityId
        self.service = service
    }

    enum CodingKeys: String, CodingKey {
        case command
        case entityId = "entity_id"
        case service
    }
}

// MARK: - PresenceEvent

public enum PresenceEvent: String, Codable, Sendable {
    case arrivedHome = "arrived_home"
    case leftHome = "left_home"
}
