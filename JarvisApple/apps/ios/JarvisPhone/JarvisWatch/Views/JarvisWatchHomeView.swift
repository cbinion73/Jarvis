import SwiftUI
import WatchKit

/// Glanceable home screen — the first thing you see on the Watch.
struct JarvisWatchHomeView: View {

    @EnvironmentObject var vm: WatchViewModel

    var body: some View {
        ScrollView {
            VStack(spacing: 10) {

                // ── Header ──────────────────────────────────────────
                VStack(spacing: 2) {
                    Text("J·A·R·V·I·S")
                        .font(.system(size: 11, weight: .semibold, design: .monospaced))
                        .foregroundStyle(.cyan.opacity(0.7))
                        .kerning(2)
                    Text(vm.greeting)
                        .font(.headline)
                        .foregroundStyle(.white)
                        .multilineTextAlignment(.center)
                    Text(vm.mode.capitalized)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                .padding(.top, 4)

                // ── Needs alert ─────────────────────────────────────
                if vm.needsCount > 0 {
                    NavigationLink(destination: NeedsWatchView()) {
                        HStack(spacing: 6) {
                            Image(systemName: "exclamationmark.circle.fill")
                                .foregroundStyle(.orange)
                            Text("\(vm.needsCount) need\(vm.needsCount == 1 ? "s" : "") you")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.orange)
                            Spacer()
                            Image(systemName: "chevron.right")
                                .font(.caption2)
                                .foregroundStyle(.orange.opacity(0.6))
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                        .background(Color.orange.opacity(0.15))
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10)
                                .strokeBorder(Color.orange.opacity(0.35), lineWidth: 0.5)
                        )
                    }
                    .buttonStyle(.plain)
                }

                // ── Nav cards ───────────────────────────────────────
                NavigationLink(destination: BriefingWatchView()) {
                    HomeNavCard(icon: "brain.head.profile", label: "Brief", color: .cyan)
                }
                .buttonStyle(.plain)

                NavigationLink(destination: WeatherWatchView()) {
                    HomeNavCard(icon: weatherIcon(vm.weatherVisualKey ?? "cloudy"),
                                label: vm.weatherTemp == "--°" ? "Weather" : vm.weatherTemp,
                                color: .blue)
                }
                .buttonStyle(.plain)

                NavigationLink(destination: VoiceCommandView()) {
                    HomeNavCard(icon: "mic.circle.fill", label: "Speak to JARVIS", color: .purple)
                }
                .buttonStyle(.plain)

                // ── Last sync ────────────────────────────────────────
                if let ts = vm.lastUpdate {
                    Text("Synced \(ts.formatted(.relative(presentation: .named)))")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .padding(.top, 2)
                }
            }
            .padding(.horizontal, 8)
            .padding(.bottom, 8)
        }
        .navigationTitle("JARVIS")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear { vm.playHapticIfNeeded() }
    }
}

// MARK: - Home nav card

private struct HomeNavCard: View {
    let icon:  String
    let label: String
    let color: Color

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(color)
                .frame(width: 28)
            Text(label)
                .font(.subheadline.weight(.medium))
                .foregroundStyle(.white)
            Spacer()
            Image(systemName: "chevron.right")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 9)
        .background(Color.white.opacity(0.07))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }
}

// MARK: - Weather visual key → SF Symbol

func weatherIcon(_ key: String) -> String {
    switch key {
    case "clear_day":            return "sun.max.fill"
    case "clear_night":          return "moon.stars.fill"
    case "partly_cloudy_day":    return "cloud.sun.fill"
    case "partly_cloudy_night":  return "cloud.moon.fill"
    case "cloudy":               return "cloud.fill"
    case "fog":                  return "cloud.fog.fill"
    case "drizzle":              return "cloud.drizzle.fill"
    case "rain":                 return "cloud.rain.fill"
    case "heavy_rain":           return "cloud.heavyrain.fill"
    case "thunderstorm":         return "cloud.bolt.rain.fill"
    case "snow":                 return "cloud.snow.fill"
    case "sleet":                return "cloud.sleet.fill"
    case "hail":                 return "cloud.hail.fill"
    case "blizzard":             return "wind.snow"
    case "hot":                  return "thermometer.sun.fill"
    case "cold":                 return "thermometer.snowflake"
    case "windy":                return "wind"
    case "tornado":              return "tornado"
    default:                     return "cloud.fill"
    }
}
