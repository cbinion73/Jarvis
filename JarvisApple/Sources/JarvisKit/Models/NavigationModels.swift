import Foundation

public struct NavigationLocationsOverview: Codable, Sendable {
    public let preferredLocationId: String?
    public let savedLocations: [NavigationSavedLocation]

    enum CodingKeys: String, CodingKey {
        case preferredLocationId = "preferred_location_id"
        case savedLocations = "saved_locations"
    }
}

public struct NavigationSavedLocation: Codable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let address: String
    public let geography: String
    public let latitude: Double?
    public let longitude: Double?
    public let source: String
    public let notes: String
}

public struct NavigationRouteOverview: Codable, Sendable {
    public let origin: NavigationPoint
    public let destination: NavigationPoint
    public let summary: String
    public let hazardActive: Bool
    public let route: NavigationRouteShape
    public let samples: [NavigationRouteSample]

    enum CodingKeys: String, CodingKey {
        case origin, destination, summary, route, samples
        case hazardActive = "hazard_active"
    }
}

public struct NavigationPoint: Codable, Sendable {
    public let label: String
    public let lat: Double
    public let lon: Double
}

public struct NavigationRouteShape: Codable, Sendable {
    public let distanceMiles: Double?
    public let durationMinutes: Int?
    public let coordinates: [[Double]]

    enum CodingKeys: String, CodingKey {
        case coordinates
        case distanceMiles = "distance_miles"
        case durationMinutes = "duration_minutes"
    }
}

public struct NavigationRouteSample: Codable, Identifiable, Sendable {
    public var id: String { "\(lat)-\(lon)-\(condition)" }

    public let lat: Double
    public let lon: Double
    public let condition: String
    public let temperatureF: Double?
    public let rainPct: Int?
    public let wind: String
    public let alerts: [String]

    enum CodingKeys: String, CodingKey {
        case lat, lon, condition, wind, alerts
        case temperatureF = "temperature_f"
        case rainPct = "rain_pct"
    }
}

public struct NavigationStopsOverview: Codable, Sendable {
    public let sections: [NavigationStopSection]
}

public struct NavigationStopSection: Codable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let items: [NavigationStop]
}

public struct NavigationStop: Codable, Identifiable, Sendable {
    public var id: String {
        "\(name)-\(lat ?? 0)-\(lng ?? 0)-\(routeMileMarker ?? 0)"
    }

    public let name: String
    public let address: String
    public let description: String
    public let url: String
    public let lat: Double?
    public let lng: Double?
    public let rating: Double?
    public let routeMileMarker: Double?
    public let distanceFromRoute: Double?

    enum CodingKeys: String, CodingKey {
        case name, address, description, url, lat, lng, rating
        case routeMileMarker = "route_mile_marker"
        case distanceFromRoute = "distance_from_route"
    }
}
