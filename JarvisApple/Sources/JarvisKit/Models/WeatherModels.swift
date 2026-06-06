import Foundation

public struct AppleWeatherOverview: Codable, Sendable {
    public let available: Bool
    public let live: Bool
    public let stale: Bool
    public let location: String
    public let summary: String
    public let source: String
    public let fetchedAt: String
    public let current: AppleWeatherCurrent
    public let hourly: [AppleWeatherHour]
    public let daily: [AppleWeatherDay]
    public let nearTerm: AppleWeatherNearTerm?
    public let radar: AppleWeatherRadar?
    public let alerts: [AppleWeatherAlert]
    public let alertsCount: Int

    enum CodingKeys: String, CodingKey {
        case available, live, stale, location, summary, source, current, hourly, daily, radar, alerts
        case nearTerm = "near_term"
        case fetchedAt = "fetched_at"
        case alertsCount = "alerts_count"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        available = try container.decode(Bool.self, forKey: .available)
        live = try container.decode(Bool.self, forKey: .live)
        stale = try container.decode(Bool.self, forKey: .stale)
        location = try container.decode(String.self, forKey: .location)
        summary = try container.decode(String.self, forKey: .summary)
        source = try container.decode(String.self, forKey: .source)
        fetchedAt = try container.decode(String.self, forKey: .fetchedAt)
        current = try container.decode(AppleWeatherCurrent.self, forKey: .current)
        hourly = try container.decodeIfPresent([AppleWeatherHour].self, forKey: .hourly) ?? []
        daily = try container.decodeIfPresent([AppleWeatherDay].self, forKey: .daily) ?? []
        nearTerm = try container.decodeIfPresent(AppleWeatherNearTerm.self, forKey: .nearTerm)
        radar = try container.decodeIfPresent(AppleWeatherRadar.self, forKey: .radar)
        alerts = try container.decodeIfPresent([AppleWeatherAlert].self, forKey: .alerts) ?? []
        alertsCount = try container.decodeIfPresent(Int.self, forKey: .alertsCount) ?? alerts.count
    }
}

public struct AppleWeatherCurrent: Codable, Sendable {
    public let temperatureF: Double?
    public let feelsLikeF: Double?
    public let condition: String
    public let icon: String
    public let wind: String
    public let humidityPct: Int?
    public let visibilityMiles: Double?
    public let pressureHpa: Double?
    public let visualKey: String
    public let moonPhase: String
    public let moonPhaseLabel: String
    public let usingForecastFallback: Bool

    enum CodingKeys: String, CodingKey {
        case condition, icon, wind
        case temperatureF = "temperature_f"
        case feelsLikeF = "feels_like_f"
        case humidityPct = "humidity_pct"
        case visibilityMiles = "visibility_miles"
        case pressureHpa = "pressure_hpa"
        case visualKey = "visual_key"
        case moonPhase = "moon_phase"
        case moonPhaseLabel = "moon_phase_label"
        case usingForecastFallback = "using_forecast_fallback"
    }
}

public struct AppleWeatherHour: Codable, Identifiable, Sendable {
    public var id: String { "\(time)-\(forecast)-\(temperatureF ?? -999)" }

    public let time: String
    public let temperatureF: Double?
    public let rainPct: Int?
    public let forecast: String
    public let icon: String

    enum CodingKeys: String, CodingKey {
        case time, forecast, icon
        case temperatureF = "temperature_f"
        case rainPct = "rain_pct"
    }
}

public struct AppleWeatherDay: Codable, Identifiable, Sendable {
    public var id: String { "\(name)-\(high ?? -999)-\(low ?? -999)" }

    public let name: String
    public let icon: String
    public let high: Int?
    public let low: Int?
    public let rainPct: Int?
    public let forecast: String

    enum CodingKeys: String, CodingKey {
        case name, icon, high, low, forecast
        case rainPct = "rain_pct"
    }
}

public struct AppleWeatherNearTerm: Codable, Sendable {
    public let windowMinutes: Int
    public let summary: String
    public let hazardActive: Bool
    public let rainRiskPct: Int

    enum CodingKeys: String, CodingKey {
        case summary
        case windowMinutes = "window_minutes"
        case hazardActive = "hazard_active"
        case rainRiskPct = "rain_risk_pct"
    }
}

public struct AppleWeatherRadar: Codable, Sendable {
    public let available: Bool
    public let source: String
    public let station: String
    public let viewerURL: String
    public let loopImageURL: String
    public let baseVelocityLoopURL: String
    public let posture: AppleWeatherRadarPosture?

    enum CodingKeys: String, CodingKey {
        case available, source, station, posture
        case viewerURL = "viewer_url"
        case loopImageURL = "loop_image_url"
        case baseVelocityLoopURL = "base_velocity_loop_url"
    }
}

public struct AppleWeatherRadarPosture: Codable, Sendable {
    public let mode: String
    public let summary: String
    public let shouldOpen: Bool

    enum CodingKeys: String, CodingKey {
        case mode, summary
        case shouldOpen = "should_open"
    }
}

public struct AppleWeatherAlert: Codable, Identifiable, Sendable {
    public var id: String { headline.isEmpty ? event : headline }

    public let event: String
    public let severity: String
    public let headline: String
    public let description: String
}
