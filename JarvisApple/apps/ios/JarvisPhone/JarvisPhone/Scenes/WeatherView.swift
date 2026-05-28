import SwiftUI
import WeatherKit

struct WeatherView: View {

    @StateObject private var wx   = WeatherManager.shared
    @StateObject private var loc  = WeatherLocationProvider.shared

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                Group {
                    if wx.isLoading && wx.current == nil {
                        loadingView
                    } else if let cur = wx.current {
                        weatherContent(cur)
                    } else {
                        emptyState
                    }
                }
            }
            .navigationTitle(wx.locationName.isEmpty ? "Weather" : wx.locationName)
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        if let l = loc.location {
                            Task { await wx.load(location: l) }
                        } else {
                            loc.requestAndFetch()
                        }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .glassEffect(in: Circle())
                }
            }
        }
        .onChange(of: loc.location) { _, newLoc in
            guard let l = newLoc else { return }
            Task { await wx.load(location: l) }
        }
        .onAppear { loc.requestAndFetch() }
    }

    // MARK: - Loading

    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView().tint(.cyan).scaleEffect(1.4)
            Text("Fetching weather…")
                .font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Empty / no location

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "location.slash.fill")
                .font(.system(size: 44)).foregroundStyle(.secondary)
            Text("Location needed")
                .font(.headline).foregroundStyle(.white)
            Text("Allow location access so JARVIS can fetch live weather.")
                .font(.caption).foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Allow Location") { loc.requestAndFetch() }
                .buttonStyle(.borderedProminent).tint(.cyan)
        }
        .padding(24)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Main content

    @ViewBuilder
    private func weatherContent(_ cur: CurrentWeatherSnapshot) -> some View {
        ScrollView {
            VStack(spacing: 14) {

                // ── Condition banner image ──────────────────────
                WeatherManager.conditionImage(cur.visualKey)
                    .resizable()
                    .aspectRatio(contentMode: .fill)
                    .frame(maxWidth: .infinity)
                    .frame(height: 180)
                    .clipped()
                    .clipShape(RoundedRectangle(cornerRadius: 16))
                    .overlay(alignment: .bottomLeading) {
                        // Hero temp + condition on top of the image
                        VStack(alignment: .leading, spacing: 2) {
                            Text(cur.tempString)
                                .font(.system(size: 52, weight: .bold))
                                .foregroundStyle(.white)
                                .shadow(radius: 4)
                            Text(cur.condition)
                                .font(.subheadline.weight(.medium))
                                .foregroundStyle(.white.opacity(0.9))
                                .shadow(radius: 4)
                            Text(cur.feelsLikeString)
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.75))
                        }
                        .padding(14)
                    }

                // ── Stats grid ────────────────────────────────
                LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 3),
                          spacing: 10) {
                    StatTile(icon: "humidity.fill",           label: "Humidity",    value: cur.humidityString,    color: .cyan)
                    StatTile(icon: "wind",                    label: "Wind",        value: cur.wind,              color: .white)
                    StatTile(icon: "eye.fill",                label: "Visibility",  value: cur.visibilityString,  color: .blue)
                    StatTile(icon: "sun.max.fill",            label: "UV Index",    value: cur.uvString,          color: .yellow)
                    StatTile(icon: "thermometer.medium",      label: "Feels Like",  value: cur.feelsLikeString,   color: .orange)
                    StatTile(icon: "gauge.with.dots.needle.bottom.50percent",
                                                              label: "Pressure",    value: cur.pressureString,    color: .purple)
                }

                // ── Hourly scroll ──────────────────────────────
                if !wx.hourly.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        Label("Hourly", systemImage: "clock.fill")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white.opacity(0.7))
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 10) {
                                ForEach(wx.hourly) { h in
                                    HourlyTile(hour: h)
                                }
                            }
                        }
                    }
                    .padding(14)
                    .glassEffect(in: RoundedRectangle(cornerRadius: 16))
                }

                // ── 7-day forecast ─────────────────────────────
                if !wx.forecast.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        Label("7-Day Forecast", systemImage: "calendar")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white.opacity(0.7))
                        VStack(spacing: 0) {
                            ForEach(Array(wx.forecast.enumerated()), id: \.element.id) { idx, day in
                                ForecastRow(day: day)
                                if idx < wx.forecast.count - 1 {
                                    Divider().opacity(0.25)
                                }
                            }
                        }
                    }
                    .padding(14)
                    .glassEffect(in: RoundedRectangle(cornerRadius: 16))
                }

                // ── Apple Weather attribution (required by WeatherKit TOS) ──
                WeatherAttributionView()
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }
}

// MARK: - Stat tile

private struct StatTile: View {
    let icon:  String
    let label: String
    let value: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Image(systemName: icon)
                .font(.caption)
                .foregroundStyle(color)
            Text(value)
                .font(.subheadline.bold())
                .foregroundStyle(.white)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .glassEffect(in: RoundedRectangle(cornerRadius: 12))
    }
}

// MARK: - Hourly tile

private struct HourlyTile: View {
    let hour: HourForecastSnapshot

    var body: some View {
        VStack(spacing: 6) {
            Text(hour.time)
                .font(.caption2)
                .foregroundStyle(.secondary)
            // Tiny condition icon from asset
            WeatherManager.conditionImage(
                WeatherManager.visualKey(condition: .clear, isDaylight: hour.isDaylight)
            )
            .resizable()
            .aspectRatio(contentMode: .fill)
            .frame(width: 32, height: 20)
            .clipped()
            .clipShape(RoundedRectangle(cornerRadius: 4))
            Text(hour.tempString)
                .font(.subheadline.bold())
                .foregroundStyle(.white)
            if hour.precipChance > 10 {
                Text(String(format: "%.0f%%", hour.precipChance))
                    .font(.caption2)
                    .foregroundStyle(.cyan)
            }
        }
        .padding(.vertical, 8)
        .padding(.horizontal, 10)
        .glassEffect(in: RoundedRectangle(cornerRadius: 10))
    }
}

// MARK: - Forecast row

private struct ForecastRow: View {
    let day: DayForecastSnapshot

    var body: some View {
        HStack(spacing: 12) {
            Text(day.name)
                .font(.subheadline)
                .foregroundStyle(.white)
                .frame(width: 38, alignment: .leading)

            WeatherManager.conditionImage(day.visualKey)
                .resizable()
                .aspectRatio(contentMode: .fill)
                .frame(width: 36, height: 24)
                .clipped()
                .clipShape(RoundedRectangle(cornerRadius: 4))

            Text(day.condition)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)

            Spacer()

            if day.precipChance > 10 {
                Text(day.precipString)
                    .font(.caption2)
                    .foregroundStyle(.cyan)
                    .frame(width: 30, alignment: .trailing)
            } else {
                Spacer().frame(width: 30)
            }

            Text(day.lowString)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .frame(width: 30, alignment: .trailing)

            Text(day.highString)
                .font(.subheadline.bold())
                .foregroundStyle(.white)
                .frame(width: 30, alignment: .trailing)
        }
        .padding(.vertical, 8)
    }
}

// MARK: - Apple attribution (legally required by WeatherKit TOS)

private struct WeatherAttributionView: View {
    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "apple.logo")
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text("Weather data provided by Apple Weather")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.bottom, 8)
    }
}

#Preview {
    WeatherView()
}
