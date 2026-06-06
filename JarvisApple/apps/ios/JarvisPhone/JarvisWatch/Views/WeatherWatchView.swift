import SwiftUI

/// Compact weather display for Apple Watch.
/// Data is pushed from the iPhone via WatchConnectivity.
struct WeatherWatchView: View {

    @EnvironmentObject var vm: WatchViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {

                // ── Condition icon + temp ─────────────────────────
                HStack(alignment: .center, spacing: 10) {
                    Image(systemName: weatherIcon(vm.weatherVisualKey ?? "cloudy"))
                        .font(.system(size: 36, weight: .medium))
                        .foregroundStyle(weatherColor(vm.weatherVisualKey ?? "cloudy"))
                        .symbolRenderingMode(.multicolor)

                    VStack(alignment: .leading, spacing: 2) {
                        Text(vm.weatherTemp)
                            .font(.system(size: 34, weight: .bold).monospacedDigit())
                            .foregroundStyle(.white)
                        Text(vm.weatherCondition.isEmpty ? "—" : vm.weatherCondition)
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.8))
                        if !vm.weatherFeelsLike.isEmpty {
                            Text("Feels \(vm.weatherFeelsLike)")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                // ── Mini stats ────────────────────────────────────
                HStack(spacing: 10) {
                    if !vm.weatherHumidity.isEmpty {
                        MiniWeatherStat(icon: "humidity.fill",  value: vm.weatherHumidity, color: .cyan)
                    }
                    if !vm.weatherWind.isEmpty {
                        MiniWeatherStat(icon: "wind",            value: vm.weatherWind,     color: .white.opacity(0.8))
                    }
                }

                // ── 3-day forecast ────────────────────────────────
                if !vm.weatherForecast.isEmpty {
                    Divider().opacity(0.25)
                    HStack(spacing: 0) {
                        ForEach(vm.weatherForecast.prefix(3), id: \.self) { item in
                            WatchForecastCell(item: item)
                        }
                    }
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
        }
        .navigationTitle("Weather")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - Mini stat

private struct MiniWeatherStat: View {
    let icon:  String
    let value: String
    let color: Color

    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: icon)
                .font(.caption2)
                .foregroundStyle(color)
            Text(value)
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.85))
        }
    }
}

// MARK: - Forecast cell

private struct WatchForecastCell: View {
    let item: [String: String]

    var body: some View {
        VStack(spacing: 3) {
            Text(item["name"] ?? "—")
                .font(.caption2)
                .foregroundStyle(.secondary)
            if let key = item["condition"] {
                Image(systemName: weatherIcon(key))
                    .font(.caption2)
                    .foregroundStyle(weatherColor(key))
                    .symbolRenderingMode(.multicolor)
            }
            Text(item["high"] ?? "—")
                .font(.caption.bold())
                .foregroundStyle(.white)
            Text(item["low"] ?? "—")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }
}

// MARK: - Visual key → color accent

func weatherColor(_ key: String) -> Color {
    switch key {
    case "clear_day", "hot":            return .yellow
    case "clear_night":                 return .indigo
    case "partly_cloudy_day":           return .orange
    case "partly_cloudy_night":         return .purple
    case "thunderstorm":                return .yellow
    case "snow", "blizzard", "cold":    return .cyan
    case "rain", "heavy_rain", "sleet": return .blue
    case "hail":                        return .teal
    case "windy", "tornado":            return .mint
    default:                            return .gray
    }
}
