import Foundation

public struct NavigationLocationsOverview: Codable, Sendable {
    public let preferredLocationId: String?
    public let savedLocations: [NavigationSavedLocation]
    public let navigationState: NavigationState?

    enum CodingKeys: String, CodingKey {
        case preferredLocationId = "preferred_location_id"
        case savedLocations = "saved_locations"
        case navigationState = "navigation_state"
    }
}

public struct NavigationState: Codable, Sendable {
    public let favoriteDestinations: [String]
    public let recentDestinations: [String]
    public let routeHistory: [NavigationRouteHistoryEntry]
    public let activeStopCategoryIDs: [String]
    public let parksHistoricRadiusMiles: Int
    public let selectedOriginMode: String
    public let selectedSavedLocationID: String
    public let lastRoute: NavigationLastRoute

    enum CodingKeys: String, CodingKey {
        case favoriteDestinations = "favorite_destinations"
        case recentDestinations = "recent_destinations"
        case routeHistory = "route_history"
        case activeStopCategoryIDs = "active_stop_category_ids"
        case parksHistoricRadiusMiles = "parks_historic_radius_miles"
        case selectedOriginMode = "selected_origin_mode"
        case selectedSavedLocationID = "selected_saved_location_id"
        case lastRoute = "last_route"
    }
}

public struct NavigationLastRoute: Codable, Sendable {
    public let origin: String
    public let destination: String

    public init(origin: String, destination: String) {
        self.origin = origin
        self.destination = destination
    }
}

public struct NavigationRouteHistoryEntry: Codable, Identifiable, Sendable {
    public let routeID: String
    public let origin: String
    public let destination: String
    public let originMode: String
    public let savedLocationID: String
    public let sourceLabel: String
    public let savedAt: String
    public let lastPreviewedAt: String
    public let lastResumedAt: String
    public let previewCount: Int
    public let resumeCount: Int

    public var id: String { routeID }

    enum CodingKeys: String, CodingKey {
        case routeID = "route_id"
        case origin
        case destination
        case originMode = "origin_mode"
        case savedLocationID = "saved_location_id"
        case sourceLabel = "source_label"
        case savedAt = "saved_at"
        case lastPreviewedAt = "last_previewed_at"
        case lastResumedAt = "last_resumed_at"
        case previewCount = "preview_count"
        case resumeCount = "resume_count"
    }
}

public struct NavigationStatePatch: Codable, Sendable {
    public let favoriteDestinations: [String]?
    public let recentDestinations: [String]?
    public let activeStopCategoryIDs: [String]?
    public let parksHistoricRadiusMiles: Int?
    public let selectedOriginMode: String?
    public let selectedSavedLocationID: String?
    public let lastRoute: NavigationLastRoute?

    public init(
        favoriteDestinations: [String]? = nil,
        recentDestinations: [String]? = nil,
        activeStopCategoryIDs: [String]? = nil,
        parksHistoricRadiusMiles: Int? = nil,
        selectedOriginMode: String? = nil,
        selectedSavedLocationID: String? = nil,
        lastRoute: NavigationLastRoute? = nil
    ) {
        self.favoriteDestinations = favoriteDestinations
        self.recentDestinations = recentDestinations
        self.activeStopCategoryIDs = activeStopCategoryIDs
        self.parksHistoricRadiusMiles = parksHistoricRadiusMiles
        self.selectedOriginMode = selectedOriginMode
        self.selectedSavedLocationID = selectedSavedLocationID
        self.lastRoute = lastRoute
    }

    enum CodingKeys: String, CodingKey {
        case favoriteDestinations = "favorite_destinations"
        case recentDestinations = "recent_destinations"
        case activeStopCategoryIDs = "active_stop_category_ids"
        case parksHistoricRadiusMiles = "parks_historic_radius_miles"
        case selectedOriginMode = "selected_origin_mode"
        case selectedSavedLocationID = "selected_saved_location_id"
        case lastRoute = "last_route"
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
    public let steps: [NavigationRouteStep]

    enum CodingKeys: String, CodingKey {
        case coordinates, steps
        case distanceMiles = "distance_miles"
        case durationMinutes = "duration_minutes"
    }
}

public struct NavigationRouteStep: Codable, Identifiable, Sendable {
    public var id: String { "\(sequence)-\(instruction)" }

    public let sequence: Int
    public let instruction: String
    public let distanceMiles: Double?
    public let durationMinutes: Int?
    public let maneuver: String
    public let modifier: String
    public let name: String

    enum CodingKeys: String, CodingKey {
        case sequence, instruction, maneuver, modifier, name
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
