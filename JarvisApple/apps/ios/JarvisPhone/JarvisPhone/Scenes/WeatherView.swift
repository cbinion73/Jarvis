import SwiftUI
import WeatherKit

// MARK: - WeatherView  "The Observatory"

struct WeatherView: View {

    // Singletons — use @ObservedObject so SwiftUI doesn't take duplicate ownership.
    @ObservedObject private var wx  = WeatherManager.shared
    @ObservedObject private var loc = WeatherLocationProvider.shared

    private let sky = Color(red: 0.4, green: 0.75, blue: 1.0)

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                Group {
                    if let cur = wx.current {
                        // ── Have data — show it (even while a background refresh runs)
                        weatherContent(cur)
                    } else if wx.isLoading {
                        // ── Weather fetch in progress
                        loadingView
                    } else if loc.authorizationStatus == .denied
                           || loc.authorizationStatus == .restricted {
                        // ── User explicitly denied permission
                        deniedState
                    } else {
                        // ── Authorized but waiting for first GPS fix
                        locatingView
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
        .onAppear {
            loc.requestAndFetch()
            // If a cached location was restored before this view appeared,
            // onChange won't fire — load weather immediately in that case.
            if let l = loc.location, wx.current == nil {
                Task { await wx.load(location: l) }
            }
        }
    }

    // MARK: - Loading

    private var loadingView: some View {
        VStack(spacing: 16) {
            Image(systemName: "cloud.sun.fill")
                .font(.system(size: 40))
                .foregroundStyle(sky.opacity(0.4))
                .symbolEffect(.pulse)
            Text("Fetching weather…")
                .font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Waiting for GPS fix (permission already granted)

    private var locatingView: some View {
        VStack(spacing: 14) {
            Image(systemName: "location.circle.fill")
                .font(.system(size: 48)).foregroundStyle(sky.opacity(0.6))
                .symbolEffect(.pulse)
            Text("Finding your location…")
                .font(.headline).foregroundStyle(.white)
            Text("JARVIS has location access. Getting a fix…")
                .font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
        }
        .padding(24)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .onAppear { loc.requestAndFetch() }
    }

    // MARK: - Location permission denied

    private var deniedState: some View {
        VStack(spacing: 16) {
            Image(systemName: "location.slash.fill")
                .font(.system(size: 44)).foregroundStyle(.secondary)
            Text("Location access denied")
                .font(.headline).foregroundStyle(.white)
            Text("Enable Location for JARVIS in Settings → Privacy → Location Services.")
                .font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
            Button("Open Settings") {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
            }
            .buttonStyle(.borderedProminent).tint(sky)
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

                // ── Hero image — taller, cinematic ─────────────────
                WeatherManager.conditionImage(cur.visualKey)
                    .resizable()
                    .aspectRatio(contentMode: .fill)
                    .frame(maxWidth: .infinity)
                    .frame(height: 240)
                    .clipped()
                    .clipShape(RoundedRectangle(cornerRadius: 20))
                    .overlay(
                        // Gradient overlay so text is always legible
                        LinearGradient(
                            colors: [.clear, .black.opacity(0.7)],
                            startPoint: UnitPoint(x: 0.5, y: 0.25),
                            endPoint: .bottom
                        )
                        .clipShape(RoundedRectangle(cornerRadius: 20))
                    )
                    .overlay(alignment: .bottomLeading) {
                        VStack(alignment: .leading, spacing: 0) {
                            Text(cur.tempString)
                                .font(.system(size: 68, weight: .bold))
                                .foregroundStyle(.white)
                                .shadow(radius: 2)
                            Text(cur.condition)
                                .font(.title3.weight(.semibold))
                                .foregroundStyle(.white.opacity(0.9))
                            Text(cur.feelsLikeString)
                                .font(.subheadline)
                                .foregroundStyle(.white.opacity(0.65))
                        }
                        .padding(18)
                    }

                // ── Stats grid — colored icon backgrounds ──────────
                LazyVGrid(
                    columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 3),
                    spacing: 10
                ) {
                    ObsTile(icon: "humidity.fill",          label: "Humidity",   value: cur.humidityString,   color: sky)
                    ObsTile(icon: "wind",                   label: "Wind",       value: cur.wind,             color: .white)
                    ObsTile(icon: "eye.fill",               label: "Visibility", value: cur.visibilityString, color: .blue)
                    ObsTile(icon: "sun.max.fill",           label: "UV Index",   value: cur.uvString,         color: .yellow)
                    ObsTile(icon: "thermometer.medium",     label: "Feels Like", value: cur.feelsLikeString,  color: .orange)
                    ObsTile(icon: "gauge.with.dots.needle.bottom.50percent",
                                                            label: "Pressure",   value: cur.pressureString,   color: .purple)
                }

                // ── Hourly ─────────────────────────────────────────
                if !wx.hourly.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        HStack(spacing: 6) {
                            Image(systemName: "clock.fill")
                                .font(.system(size: 11, weight: .semibold))
                                .foregroundStyle(sky)
                            Text("HOURLY")
                                .font(.system(size: 10, weight: .bold))
                                .tracking(1.0)
                                .foregroundStyle(sky.opacity(0.85))
                        }
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                ForEach(wx.hourly) { h in ObsHourTile(hour: h, sky: sky) }
                            }
                        }
                    }
                    .padding(14)
                    .glassEffect(in: RoundedRectangle(cornerRadius: 16))
                }

                // ── 7-day forecast ─────────────────────────────────
                if !wx.forecast.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        HStack(spacing: 6) {
                            Image(systemName: "calendar")
                                .font(.system(size: 11, weight: .semibold))
                                .foregroundStyle(sky)
                            Text("7-DAY")
                                .font(.system(size: 10, weight: .bold))
                                .tracking(1.0)
                                .foregroundStyle(sky.opacity(0.85))
                        }
                        VStack(spacing: 0) {
                            ForEach(Array(wx.forecast.enumerated()), id: \.element.id) { idx, day in
                                ObsForecastRow(day: day, sky: sky)
                                if idx < wx.forecast.count - 1 {
                                    Divider().opacity(0.18)
                                }
                            }
                        }
                    }
                    .padding(14)
                    .glassEffect(in: RoundedRectangle(cornerRadius: 16))
                }

                // ── Apple attribution (legally required by WeatherKit TOS) ──
                HStack(spacing: 6) {
                    Image(systemName: "apple.logo")
                        .font(.caption2).foregroundStyle(.secondary)
                    Text("Weather data provided by Apple Weather")
                        .font(.caption2).foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.bottom, 8)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }
}

// MARK: - Observatory stat tile

private struct ObsTile: View {
    let icon:  String
    let label: String
    let value: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            // Colored icon pill
            HStack(spacing: 5) {
                Image(systemName: icon)
                    .font(.system(size: 11))
                    .foregroundStyle(color)
                    .frame(width: 20, height: 20)
                    .background(color.opacity(0.12), in: RoundedRectangle(cornerRadius: 6))
            }
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

private struct ObsHourTile: View {
    let hour: HourForecastSnapshot
    let sky: Color

    var tempColor: Color {
        // Cool (< 40°F) → blue, warm (> 80°F) → orange, neutral in between
        let temp = Double(hour.tempString.filter { $0.isNumber || $0 == "-" }) ?? 65
        if temp < 45 { return Color(red: 0.5, green: 0.7, blue: 1.0) }
        if temp > 80 { return Color(red: 1.0, green: 0.5, blue: 0.2) }
        return .white
    }

    var body: some View {
        VStack(spacing: 5) {
            Text(hour.time).font(.caption2).foregroundStyle(.secondary)

            WeatherManager.conditionImage(
                WeatherManager.visualKey(condition: .clear, isDaylight: hour.isDaylight)
            )
            .resizable()
            .aspectRatio(contentMode: .fill)
            .frame(width: 30, height: 20)
            .clipped()
            .clipShape(RoundedRectangle(cornerRadius: 4))

            Text(hour.tempString)
                .font(.subheadline.bold().monospacedDigit())
                .foregroundStyle(tempColor)

            if hour.precipChance > 10 {
                Text(String(format: "%.0f%%", hour.precipChance))
                    .font(.caption2).foregroundStyle(sky)
            } else {
                Color.clear.frame(height: 12)
            }
        }
        .padding(.vertical, 8)
        .padding(.horizontal, 10)
        .glassEffect(in: RoundedRectangle(cornerRadius: 10))
    }
}

// MARK: - Forecast row

private struct ObsForecastRow: View {
    let day: DayForecastSnapshot
    let sky: Color

    var body: some View {
        HStack(spacing: 10) {
            Text(day.name)
                .font(.subheadline)
                .foregroundStyle(.white)
                .frame(width: 38, alignment: .leading)

            WeatherManager.conditionImage(day.visualKey)
                .resizable().aspectRatio(contentMode: .fill)
                .frame(width: 32, height: 22)
                .clipped().clipShape(RoundedRectangle(cornerRadius: 4))

            Text(day.condition)
                .font(.caption).foregroundStyle(.secondary).lineLimit(1)

            Spacer()

            if day.precipChance > 10 {
                Text(day.precipString)
                    .font(.caption2).foregroundStyle(sky).frame(width: 30, alignment: .trailing)
            } else {
                Spacer().frame(width: 30)
            }

            // Temp range bar
            HStack(spacing: 4) {
                Text(day.lowString)
                    .font(.subheadline.monospacedDigit())
                    .foregroundStyle(.secondary)
                    .frame(width: 30, alignment: .trailing)
                Text(day.highString)
                    .font(.subheadline.bold().monospacedDigit())
                    .foregroundStyle(.white)
                    .frame(width: 30, alignment: .trailing)
            }
        }
        .padding(.vertical, 9)
    }
}

#Preview {
    WeatherView()
}
