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
    public let alertsCount: Int

    enum CodingKeys: String, CodingKey {
        case available, live, stale, location, summary, source, current, hourly
        case fetchedAt = "fetched_at"
        case alertsCount = "alerts_count"
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
    public let usingForecastFallback: Bool

    enum CodingKeys: String, CodingKey {
        case condition, icon, wind
        case temperatureF = "temperature_f"
        case feelsLikeF = "feels_like_f"
        case humidityPct = "humidity_pct"
        case visibilityMiles = "visibility_miles"
        case pressureHpa = "pressure_hpa"
        case visualKey = "visual_key"
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
