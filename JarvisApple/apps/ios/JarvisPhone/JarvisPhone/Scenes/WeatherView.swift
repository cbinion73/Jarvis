import SwiftUI
import WeatherKit
import JarvisKit

// MARK: - WeatherView  "The Observatory"

struct WeatherView: View {
    // Singletons — use @ObservedObject so SwiftUI doesn't take duplicate ownership.
    @ObservedObject private var wx  = WeatherManager.shared
    @ObservedObject private var loc = WeatherLocationProvider.shared

    @State private var serverWeather: AppleWeatherOverview?
    @State private var serverWeatherError: String?
    @State private var isLoadingServerWeather = false
    @State private var routeWeather: NavigationRouteOverview?
    @State private var routeWeatherError: String?
    @State private var isLoadingRouteWeather = false

    private let sky = Color(red: 0.4, green: 0.75, blue: 1.0)

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                Group {
                    if let cur = wx.current {
                        // ── Have data — show it (even while a background refresh runs)
                        weatherContent(cur)
                    } else if let serverWeather {
                        serverWeatherContent(serverWeather)
                    } else if wx.isLoading || isLoadingServerWeather {
                        // ── Weather fetch in progress
                        loadingView
                    } else if loc.authorizationStatus == .denied
                           || loc.authorizationStatus == .restricted {
                        // ── User explicitly denied permission
                        deniedState
                    } else if loc.lastErrorMessage != nil && !loc.isRequestingLocation {
                        locationProblemView
                    } else if loc.authorizationStatus == .authorizedWhenInUse
                           || loc.authorizationStatus == .authorizedAlways {
                        // ── Authorized but waiting for first GPS fix
                        locatingView
                    } else {
                        serverWeatherUnavailableView
                    }
                }
            }
            .navigationTitle(wx.locationName.isEmpty ? "Weather" : wx.locationName)
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await refreshWeatherSurfaces(force: true) }
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
            Task { await refreshWeatherSurfaces(force: false) }
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
            Text(loc.lastErrorMessage
                 ?? (loc.isRequestingLocation
                     ? "JARVIS has location access. Getting a fix…"
                     : "JARVIS is using server weather. Phone location is optional."))
                .font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
            if !loc.isRequestingLocation {
                Button("Use Phone Location") {
                    loc.requestAndFetch(force: true, userInitiated: true)
                }
                .buttonStyle(.borderedProminent).tint(sky)
            }
        }
        .padding(24)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var serverWeatherUnavailableView: some View {
        VStack(spacing: 14) {
            Image(systemName: "cloud.sun.fill")
                .font(.system(size: 48)).foregroundStyle(sky.opacity(0.6))
            Text("Weather unavailable")
                .font(.headline).foregroundStyle(.white)
            Text(serverWeatherError ?? "JARVIS could not load server weather.")
                .font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
            Button("Retry") {
                Task { await loadServerWeather(force: true) }
            }
            .buttonStyle(.borderedProminent).tint(sky)
        }
        .padding(24)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var locationProblemView: some View {
        VStack(spacing: 14) {
            Image(systemName: "location.magnifyingglass")
                .font(.system(size: 48)).foregroundStyle(sky.opacity(0.6))
            Text("Couldn't find your location")
                .font(.headline).foregroundStyle(.white)
            Text(loc.lastErrorMessage ?? "JARVIS could not get a location fix.")
                .font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
            Button("Try Again") {
                loc.requestAndFetch(force: true, userInitiated: true)
            }
            .buttonStyle(.borderedProminent).tint(sky)
        }
        .padding(24)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
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
                weatherHeroCard(
                    imageKey: cur.visualKey,
                    temperatureText: cur.tempString,
                    title: cur.condition,
                    subtitle: cur.feelsLikeString
                )

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

                if let overview = serverWeather {
                    stormCenterSection(for: overview)
                }

                routeWeatherMonitorSection

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

    @ViewBuilder
    private func serverWeatherContent(_ overview: AppleWeatherOverview) -> some View {
        let cur = overview.current
        ScrollView {
            VStack(spacing: 14) {
                weatherHeroCard(
                    imageKey: serverHeroImageKey(for: cur),
                    eyebrow: overview.location.isEmpty ? "JARVIS Weather" : overview.location,
                    badge: overview.stale ? "STALE" : nil,
                    temperatureText: cur.temperatureF.map { "\(Int($0.rounded()))°" } ?? "--°",
                    title: cur.condition.isEmpty ? overview.summary : cur.condition,
                    subtitle: serverHeroSubtitle(for: cur),
                    footnote: serverHeroFootnote(for: overview)
                )

                LazyVGrid(
                    columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 2),
                    spacing: 10
                ) {
                    ServerWeatherTile(label: "Wind", value: cur.wind.isEmpty ? "--" : cur.wind, icon: "wind", color: .white)
                    ServerWeatherTile(label: "Humidity", value: cur.humidityPct.map { "\($0)%" } ?? "--", icon: "humidity.fill", color: sky)
                    ServerWeatherTile(label: "Visibility", value: cur.visibilityMiles.map { String(format: "%.1f mi", $0) } ?? "--", icon: "eye.fill", color: .blue)
                    ServerWeatherTile(label: "Pressure", value: cur.pressureHpa.map { "\(Int($0.rounded())) hPa" } ?? "--", icon: "gauge.with.dots.needle.bottom.50percent", color: .purple)
                }

                if !overview.hourly.isEmpty {
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
                                ForEach(overview.hourly) { hour in
                                    ServerHourTile(hour: hour, sky: sky)
                                }
                            }
                        }
                    }
                    .padding(14)
                    .glassEffect(in: RoundedRectangle(cornerRadius: 16))
                }

                stormCenterSection(for: overview)
                routeWeatherMonitorSection
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    @ViewBuilder
    private func weatherHeroCard(
        imageKey: String,
        eyebrow: String? = nil,
        badge: String? = nil,
        temperatureText: String,
        title: String,
        subtitle: String? = nil,
        footnote: String? = nil
    ) -> some View {
        WeatherManager.conditionImage(imageKey)
            .resizable()
            .aspectRatio(contentMode: .fill)
            .frame(maxWidth: .infinity)
            .frame(height: 240)
            .clipped()
            .clipShape(RoundedRectangle(cornerRadius: 20))
            .overlay(
                LinearGradient(
                    colors: [.clear, .black.opacity(0.75)],
                    startPoint: UnitPoint(x: 0.5, y: 0.25),
                    endPoint: .bottom
                )
                .clipShape(RoundedRectangle(cornerRadius: 20))
            )
            .overlay(alignment: .topLeading) {
                if eyebrow != nil || badge != nil {
                    HStack(alignment: .top) {
                        if let eyebrow, !eyebrow.isEmpty {
                            Text(eyebrow)
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.white.opacity(0.92))
                                .padding(.horizontal, 10)
                                .padding(.vertical, 6)
                                .background(.black.opacity(0.22), in: Capsule())
                        }
                        Spacer()
                        if let badge, !badge.isEmpty {
                            Text(badge)
                                .font(.system(size: 9, weight: .black))
                                .foregroundStyle(.black)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(.orange, in: Capsule())
                        }
                    }
                    .padding(16)
                }
            }
            .overlay(alignment: .bottomLeading) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(temperatureText)
                        .font(.system(size: 68, weight: .bold))
                        .foregroundStyle(.white)
                        .shadow(radius: 2)
                    Text(title)
                        .font(.title3.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.92))
                    if let subtitle, !subtitle.isEmpty {
                        Text(subtitle)
                            .font(.subheadline)
                            .foregroundStyle(.white.opacity(0.72))
                    }
                    if let footnote, !footnote.isEmpty {
                        Text(footnote)
                            .font(.caption2.weight(.medium))
                            .foregroundStyle(.white.opacity(0.85))
                            .padding(.top, 6)
                    }
                }
                .padding(18)
            }
    }

    @ViewBuilder
    private func stormCenterSection(for overview: AppleWeatherOverview) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 6) {
                Image(systemName: "cloud.bolt.rain.fill")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(sky)
                Text("STORM CENTER")
                    .font(.system(size: 10, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(sky.opacity(0.85))
                Spacer()
                if overview.alertsCount > 0 {
                    Text("\(overview.alertsCount) alert\(overview.alertsCount == 1 ? "" : "s")")
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(.black)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(.orange, in: Capsule())
                }
            }

            if let nearTerm = overview.nearTerm {
                nearTermCard(nearTerm)
            }

            if !overview.alerts.isEmpty {
                alertsSection(overview.alerts)
            }

            if let radar = overview.radar, radar.available {
                radarSection(radar)
            }

            if !overview.daily.isEmpty {
                dailyOutlookSection(overview.daily)
            }
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    @ViewBuilder
    private var routeWeatherMonitorSection: some View {
        if isLoadingRouteWeather || routeWeather != nil || routeWeatherError != nil {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 6) {
                    Image(systemName: "car.fill")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(sky)
                    Text("TRAVEL WEATHER")
                        .font(.system(size: 10, weight: .bold))
                        .tracking(1.0)
                        .foregroundStyle(sky.opacity(0.85))
                    Spacer()
                    if isLoadingRouteWeather {
                        ProgressView()
                            .tint(sky)
                    }
                }

                if let routeWeather {
                    routeWeatherSummary(routeWeather)
                } else if let routeWeatherError {
                    Text(routeWeatherError)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(14)
            .glassEffect(in: RoundedRectangle(cornerRadius: 16))
        }
    }

    private func nearTermCard(_ nearTerm: AppleWeatherNearTerm) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Next \(nearTerm.windowMinutes) Minutes")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.white.opacity(0.68))
            Text(nearTerm.summary)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.white)
                .fixedSize(horizontal: false, vertical: true)
            HStack(spacing: 10) {
                ServerWeatherTile(
                    label: "Rain Risk",
                    value: "\(nearTerm.rainRiskPct)%",
                    icon: "cloud.rain.fill",
                    color: nearTerm.rainRiskPct >= 40 ? .orange : sky
                )
                ServerWeatherTile(
                    label: "Posture",
                    value: nearTerm.hazardActive ? "Watch Now" : "Steady",
                    icon: nearTerm.hazardActive ? "exclamationmark.triangle.fill" : "checkmark.circle.fill",
                    color: nearTerm.hazardActive ? .orange : .green
                )
            }
        }
    }

    private func alertsSection(_ alerts: [AppleWeatherAlert]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Active Weather Alerts")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.orange.opacity(0.95))
            ForEach(alerts.prefix(3)) { alert in
                VStack(alignment: .leading, spacing: 4) {
                    Text(alert.headline.isEmpty ? alert.event : alert.headline)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.white)
                    let detail = [alert.severity.capitalized, alert.description]
                        .filter { !$0.isEmpty }
                        .joined(separator: " · ")
                    if !detail.isEmpty {
                        Text(detail)
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.74))
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(12)
                .background(.orange.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
            }
        }
    }

    private func radarSection(_ radar: AppleWeatherRadar) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Radar")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.68))
                    if let posture = radar.posture, !posture.summary.isEmpty {
                        Text(posture.summary)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
                if let viewerURL = URL(string: radar.viewerURL), !radar.viewerURL.isEmpty {
                    Link(destination: viewerURL) {
                        Label("Open NOAA", systemImage: "arrow.up.right.square")
                            .font(.caption.weight(.semibold))
                    }
                    .buttonStyle(.bordered)
                    .tint(.white)
                }
            }

            if let loopURL = URL(string: radar.loopImageURL), !radar.loopImageURL.isEmpty {
                AsyncImage(url: loopURL) { image in
                    image
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                } placeholder: {
                    ZStack {
                        RoundedRectangle(cornerRadius: 14)
                            .fill(.white.opacity(0.04))
                        ProgressView()
                            .tint(sky)
                    }
                }
                .frame(height: 170)
                .clipShape(RoundedRectangle(cornerRadius: 14))
            }
        }
    }

    private func dailyOutlookSection(_ daily: [AppleWeatherDay]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Storm Forecast")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.white.opacity(0.68))
            VStack(spacing: 0) {
                ForEach(Array(daily.prefix(5).enumerated()), id: \.element.id) { index, day in
                    stormForecastRow(day)
                    if index < min(daily.count, 5) - 1 {
                        Divider().opacity(0.18)
                    }
                }
            }
        }
    }

    private func stormForecastRow(_ day: AppleWeatherDay) -> some View {
        HStack(spacing: 10) {
            Text(day.name)
                .font(.subheadline)
                .foregroundStyle(.white)
                .frame(width: 42, alignment: .leading)
            Text(day.icon.isEmpty ? "⛅" : day.icon)
                .font(.title3)
                .frame(width: 30)
            Text(day.forecast)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)
            Spacer()
            if let rainPct = day.rainPct, rainPct > 0 {
                Text("\(rainPct)%")
                    .font(.caption2)
                    .foregroundStyle(sky)
                    .frame(width: 34, alignment: .trailing)
            } else {
                Spacer().frame(width: 34)
            }
            HStack(spacing: 4) {
                Text(day.low.map(String.init) ?? "--")
                    .font(.subheadline.monospacedDigit())
                    .foregroundStyle(.secondary)
                    .frame(width: 28, alignment: .trailing)
                Text(day.high.map(String.init) ?? "--")
                    .font(.subheadline.bold().monospacedDigit())
                    .foregroundStyle(.white)
                    .frame(width: 28, alignment: .trailing)
            }
        }
        .padding(.vertical, 9)
    }

    private func routeWeatherSummary(_ route: NavigationRouteOverview) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(route.destination.label)
                .font(.headline)
                .foregroundStyle(.white)
            Text(route.summary)
                .font(.caption)
                .foregroundStyle(.secondary)

            HStack(spacing: 10) {
                ServerWeatherTile(
                    label: "ETA",
                    value: route.route.durationMinutes.map { "\($0) min" } ?? "--",
                    icon: "clock.badge.checkmark.fill",
                    color: sky
                )
                ServerWeatherTile(
                    label: "Distance",
                    value: route.route.distanceMiles.map { String(format: "%.1f mi", $0) } ?? "--",
                    icon: "road.lanes",
                    color: .white
                )
            }

            if !route.samples.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Route Weather Windows")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.68))
                    ForEach(Array(route.samples.prefix(3).enumerated()), id: \.offset) { _, sample in
                        HStack(spacing: 10) {
                            Image(systemName: routeSampleIcon(for: sample))
                                .foregroundStyle(routeSampleAccent(for: sample))
                                .frame(width: 20)
                            Text(sample.condition.isEmpty ? "Clear segment" : sample.condition)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(.white)
                            Spacer()
                            Text(routeWeatherLine(for: sample))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }

            let alerts = route.samples.flatMap(\.alerts)
            if !alerts.isEmpty {
                Text(alerts.prefix(2).joined(separator: " · "))
                    .font(.caption)
                    .foregroundStyle(.orange.opacity(0.9))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func serverHeroImageKey(for current: AppleWeatherCurrent) -> String {
        let visualKey = WeatherManager.canonicalImageKey(current.visualKey)
        if visualKey == "clear_night_no_moon", !current.moonPhase.isEmpty {
            return current.moonPhase
        }
        if !visualKey.isEmpty {
            return visualKey
        }
        return "clear_day"
    }

    private func serverHeroSubtitle(for current: AppleWeatherCurrent) -> String? {
        var parts: [String] = []
        if let feels = current.feelsLikeF {
            parts.append("Feels \(Int(feels.rounded()))°")
        }
        if !current.moonPhaseLabel.isEmpty {
            parts.append(current.moonPhaseLabel)
        }
        return parts.isEmpty ? nil : parts.joined(separator: "  ·  ")
    }

    private func serverHeroFootnote(for overview: AppleWeatherOverview) -> String? {
        if overview.stale {
            return "Latest packet from \(overview.source)."
        }
        if overview.current.usingForecastFallback {
            return "Using forecast fallback while live observation catches up."
        }
        let mode = overview.live ? "Live" : "Latest"
        return "\(mode) from \(overview.source)"
    }

    private func routeSampleAccent(for sample: NavigationRouteSample) -> Color {
        let lower = sample.condition.lowercased()
        if let rainPct = sample.rainPct, rainPct >= 50 { return .orange }
        if lower.contains("storm") || lower.contains("thunder") { return .orange }
        if lower.contains("snow") || lower.contains("freez") { return .cyan }
        return sky
    }

    private func routeSampleIcon(for sample: NavigationRouteSample) -> String {
        let lower = sample.condition.lowercased()
        if lower.contains("snow") || lower.contains("freez") { return "snowflake" }
        if lower.contains("storm") || lower.contains("thunder") { return "cloud.bolt.rain.fill" }
        if lower.contains("rain") || lower.contains("shower") { return "cloud.rain.fill" }
        if lower.contains("cloud") { return "cloud.fill" }
        return "sun.max.fill"
    }

    private func routeWeatherLine(for sample: NavigationRouteSample) -> String {
        var parts: [String] = []
        if let temperature = sample.temperatureF {
            parts.append("\(Int(temperature.rounded()))°")
        }
        if let rainPct = sample.rainPct, rainPct > 0 {
            parts.append("\(rainPct)% rain")
        }
        if !sample.wind.isEmpty {
            parts.append(sample.wind)
        }
        return parts.isEmpty ? "No risk flagged" : parts.joined(separator: " • ")
    }

    private func refreshWeatherSurfaces(force: Bool) async {
        async let server: Void = loadServerWeather(force: force)
        async let route: Void = loadRouteWeather(force: force)
        _ = await (server, route)
        if let l = loc.location {
            await wx.load(location: l)
        }
    }

    private func loadServerWeather(force: Bool) async {
        if serverWeather != nil && !force { return }
        isLoadingServerWeather = true
        serverWeatherError = nil
        do {
            serverWeather = try await AppleAPIClient.shared.fetchAppleWeather()
        } catch {
            serverWeatherError = error.localizedDescription
        }
        isLoadingServerWeather = false
    }

    private func loadRouteWeather(force: Bool) async {
        if routeWeather != nil && !force { return }
        isLoadingRouteWeather = true
        routeWeatherError = nil
        defer { isLoadingRouteWeather = false }
        do {
            let state = try await AppleAPIClient.shared.fetchNavigationState()
            let lastRoute = state.lastRoute
            guard !lastRoute.origin.isEmpty, !lastRoute.destination.isEmpty else {
                routeWeather = nil
                return
            }
            routeWeather = try await AppleAPIClient.shared.fetchNavigationRoute(
                origin: lastRoute.origin,
                destination: lastRoute.destination
            )
        } catch {
            routeWeatherError = error.localizedDescription
        }
    }
}

private struct ServerWeatherTile: View {
    let label: String
    let value: String
    let icon: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            Image(systemName: icon)
                .font(.system(size: 11))
                .foregroundStyle(color)
                .frame(width: 20, height: 20)
                .background(color.opacity(0.12), in: RoundedRectangle(cornerRadius: 6))
            Text(value)
                .font(.subheadline.bold())
                .foregroundStyle(.white)
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .glassEffect(in: RoundedRectangle(cornerRadius: 12))
    }
}

private struct ServerHourTile: View {
    let hour: AppleWeatherHour
    let sky: Color

    var body: some View {
        VStack(spacing: 6) {
            Text(hour.time)
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text(hour.temperatureF.map { "\(Int($0.rounded()))°" } ?? "--")
                .font(.headline.bold())
                .foregroundStyle(.white)
            Text(hour.rainPct.map { "\($0)%" } ?? "")
                .font(.caption2)
                .foregroundStyle(sky.opacity(0.8))
        }
        .frame(width: 58)
        .padding(.vertical, 10)
        .glassEffect(in: RoundedRectangle(cornerRadius: 12))
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
