import Foundation
import WeatherKit
import CoreLocation
import SwiftUI

// MARK: - Snapshots (Sendable value types)

struct CurrentWeatherSnapshot: Sendable, Equatable {
    let temperature: Double
    let feelsLike: Double
    let condition: String
    let visualKey: String
    let humidity: Double        // 0–100 %
    let wind: String
    let visibility: Double      // miles
    let pressure: Double        // hPa
    let uvIndex: Int
    let isDaylight: Bool

    var tempString:        String { "\(Int(temperature.rounded()))°" }
    var feelsLikeString:   String { "Feels \(Int(feelsLike.rounded()))°" }
    var visibilityString:  String { String(format: "%.1f mi", visibility) }
    var pressureString:    String { "\(Int(pressure)) hPa" }
    var humidityString:    String { "\(Int(humidity))%" }
    var uvString:          String { "\(uvIndex)" }
}

struct DayForecastSnapshot: Identifiable, Sendable {
    let id     = UUID()
    let name:         String
    let high:         Double
    let low:          Double
    let condition:    String
    let visualKey:    String
    let precipChance: Double

    var highString:   String { "\(Int(high.rounded()))°" }
    var lowString:    String { "\(Int(low.rounded()))°" }
    var precipString: String { "\(Int(precipChance))%" }
}

struct HourForecastSnapshot: Identifiable, Sendable {
    let id          = UUID()
    let time:        String
    let temperature: Double
    let condition:   String
    let precipChance:Double
    let isDaylight:  Bool

    var tempString:  String { "\(Int(temperature.rounded()))°" }
}

// MARK: - Manager

@MainActor
final class WeatherManager: ObservableObject {

    static let shared = WeatherManager()

    @Published var current:  CurrentWeatherSnapshot?
    @Published var forecast: [DayForecastSnapshot]  = []
    @Published var hourly:   [HourForecastSnapshot] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var locationName: String = ""

    private let service = WeatherService()

    // MARK: - Load

    func load(location: CLLocation) async {
        isLoading    = true
        errorMessage = nil
        do {
            let weather = try await service.weather(for: location)

            // Reverse-geocode to get city name.
            // CLGeocoder is deprecated in iOS 26; using MKLocalSearch as replacement.
            if let city = await Self.reverseGeocodeCityName(for: location) {
                locationName = city
            }

            let cur = weather.currentWeather
            current = CurrentWeatherSnapshot(
                temperature: cur.temperature.converted(to: UnitTemperature.fahrenheit).value,
                feelsLike:   cur.apparentTemperature.converted(to: UnitTemperature.fahrenheit).value,
                condition:   cur.condition.accessibilityDescription,
                visualKey:   Self.visualKey(condition: cur.condition, isDaylight: cur.isDaylight),
                humidity:    cur.humidity * 100,
                wind:        "\(Int(cur.wind.speed.converted(to: UnitSpeed.milesPerHour).value)) mph \(cur.wind.compassDirection.abbreviation)",
                visibility:  cur.visibility.converted(to: UnitLength.miles).value,
                pressure:    cur.pressure.converted(to: UnitPressure.hectopascals).value,
                uvIndex:     cur.uvIndex.value,
                isDaylight:  cur.isDaylight
            )

            forecast = weather.dailyForecast.forecast.prefix(7).map { day in
                DayForecastSnapshot(
                    name:         day.date.formatted(.dateTime.weekday(.abbreviated)).uppercased(),
                    high:         day.highTemperature.converted(to: UnitTemperature.fahrenheit).value,
                    low:          day.lowTemperature.converted(to: UnitTemperature.fahrenheit).value,
                    condition:    day.condition.accessibilityDescription,
                    visualKey:    Self.visualKey(condition: day.condition, isDaylight: true),
                    precipChance: day.precipitationChance * 100
                )
            }

            hourly = weather.hourlyForecast.forecast.prefix(8).map { h in
                HourForecastSnapshot(
                    time:         h.date.formatted(.dateTime.hour()),
                    temperature:  h.temperature.converted(to: UnitTemperature.fahrenheit).value,
                    condition:    h.condition.accessibilityDescription,
                    precipChance: h.precipitationChance * 100,
                    isDaylight:   h.isDaylight
                )
            }

        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    // MARK: - Reverse geocoding

    /// Returns the locality name for `location`.
    /// CLGeocoder is deprecated in iOS 26; it still works and there is no stable
    /// MapKit replacement in the current beta — swap when Apple documents it.
    private static func reverseGeocodeCityName(for location: CLLocation) async -> String? {
        let geocoder = CLGeocoder()
        return try? await geocoder.reverseGeocodeLocation(location).first?.locality
    }

    // MARK: - Visual key mapping (matches web JARVIS _VISUAL_ASSET map)

    static func visualKey(condition: WeatherCondition, isDaylight: Bool) -> String {
        switch condition {
        case .clear, .hot:
            return isDaylight ? "clear_day" : "clear_night_no_moon"
        case .mostlyClear:
            return isDaylight ? "clear_day" : "clear_night_no_moon"
        case .partlyCloudy, .mostlyCloudy:
            return "partly_cloudy_day"
        case .cloudy:
            return "partly_cloudy_day"
        case .foggy, .haze, .smoky, .blowingDust:
            return "partly_cloudy_day"
        case .drizzle, .freezingDrizzle:
            return "light_rain"
        case .rain, .sunShowers:
            return "light_rain"
        case .heavyRain:
            return "heavy_rain"
        case .isolatedThunderstorms, .scatteredThunderstorms, .thunderstorms, .strongStorms:
            return "thunderstorm"
        case .tropicalStorm, .hurricane:
            return "thunderstorm"
        case .flurries, .snow, .sleet, .wintryMix, .freezingRain:
            return "light_snow"
        case .heavySnow:
            return "heavy_snow"
        case .blizzard:
            return "blizzard"
        case .frigid:
            return "light_snow"
        case .breezy, .windy:
            return isDaylight ? "clear_day" : "clear_night_no_moon"
        case .sunFlurries:
            return "light_snow"
        case .blowingSnow:
            return "heavy_snow"
        @unknown default:
            return isDaylight ? "clear_day" : "clear_night_no_moon"
        }
    }

    // MARK: - Image helper

    static func canonicalImageKey(_ key: String) -> String {
        switch key {
        case "clear_night":
            return "clear_night_no_moon"
        case "partly_cloudy", "cloudy", "overcast", "fog", "haze", "smoke", "windy":
            return "partly_cloudy_day"
        case "rain", "showers", "drizzle":
            return "light_rain"
        case "snow", "flurries", "sleet":
            return "light_snow"
        default:
            return key
        }
    }

    /// Loads one of the 18 bundled weather PNG assets by its visual key.
    static func conditionImage(_ key: String) -> Image {
        let canonicalKey = canonicalImageKey(key)
        if let url  = Bundle.main.url(forResource: canonicalKey, withExtension: "png"),
           let data = try? Data(contentsOf: url),
           let img  = UIImage(data: data) {
            return Image(uiImage: img)
        }
        // Graceful fallback — should never hit in production
        return Image(systemName: "cloud.fill")
    }
}

// MARK: - Wind compass direction abbreviation

extension Wind.CompassDirection {
    var abbreviation: String {
        switch self {
        case .north:          return "N"
        case .northNortheast: return "NNE"
        case .northeast:      return "NE"
        case .eastNortheast:  return "ENE"
        case .east:           return "E"
        case .eastSoutheast:  return "ESE"
        case .southeast:      return "SE"
        case .southSoutheast: return "SSE"
        case .south:          return "S"
        case .southSouthwest: return "SSW"
        case .southwest:      return "SW"
        case .westSouthwest:  return "WSW"
        case .west:           return "W"
        case .westNorthwest:  return "WNW"
        case .northwest:      return "NW"
        case .northNorthwest: return "NNW"
        @unknown default:     return "—"
        }
    }
}
