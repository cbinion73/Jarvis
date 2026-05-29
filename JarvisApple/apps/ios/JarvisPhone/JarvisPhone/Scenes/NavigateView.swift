import SwiftUI
import MapKit
import CoreLocation
import JarvisKit

// MARK: - NavigateView  "Navigate"

struct NavigateView: View {

    private enum OriginMode: String, CaseIterable, Identifiable {
        case home
        case current

        var id: String { rawValue }

        var title: String {
            switch self {
            case .home: return "Home"
            case .current: return "Current"
            }
        }
    }

    @ObservedObject private var loc = WeatherLocationProvider.shared
    @ObservedObject private var geo = GeofenceManager.shared

    @State private var cameraPosition: MapCameraPosition = .automatic
    @State private var destinationText = ""
    @State private var route: NavigationRouteOverview?
    @State private var savedLocations: [NavigationSavedLocation] = []
    @State private var preferredLocationId: String?
    @State private var recentDestinations: [String] = []
    @State private var selectedOriginMode: OriginMode = .home
    @State private var loadingRoute = false
    @State private var loadingLocations = false
    @State private var routeError: String?
    @State private var selectedSavedLocationID: String?
    @FocusState private var destinationFocused: Bool

    private let slate = Color(red: 0.4, green: 0.55, blue: 0.75)
    private static let recentDestinationsKey = "jarvis.navigate.recentDestinations"

    private var selectedSavedLocation: NavigationSavedLocation? {
        if let selectedSavedLocationID,
           let match = savedLocations.first(where: { $0.id == selectedSavedLocationID }) {
            return match
        }
        if let preferredLocationId,
           let match = savedLocations.first(where: { $0.id == preferredLocationId }) {
            return match
        }
        return savedLocations.first
    }

    private var currentCoordinate: CLLocationCoordinate2D? {
        loc.location?.coordinate
    }

    private var routePolyline: MKPolyline? {
        let coordinates = route?.route.coordinates.compactMap { pair -> CLLocationCoordinate2D? in
            guard pair.count == 2 else { return nil }
            return CLLocationCoordinate2D(latitude: pair[1], longitude: pair[0])
        } ?? []
        guard !coordinates.isEmpty else { return nil }
        return MKPolyline(coordinates: coordinates, count: coordinates.count)
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 16) {
                        mapCard
                        plannerCard

                        if !savedLocations.isEmpty || !recentDestinations.isEmpty {
                            quickDestinationsCard
                        }

                        if let route {
                            routeSummaryCard(route)
                            routeWeatherCard(route)
                        } else if let routeError {
                            routeErrorCard(routeError)
                        } else {
                            emptyStateCard
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                }
            }
            .navigationTitle("Navigate")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task {
                            await loadNavigationLocations()
                            if let route {
                                focusMap(on: route)
                            }
                        }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .glassEffect(in: Circle())
                }
            }
        }
        .task {
            restoreRecentDestinations()
            await loadNavigationLocations()
            loc.requestAndFetch()
        }
    }

    // MARK: - Cards

    private var mapCard: some View {
        Map(position: $cameraPosition) {
            if let polyline = routePolyline {
                MapPolyline(polyline)
                    .stroke(slate, lineWidth: 6)
            }

            if let route {
                Annotation("Origin", coordinate: CLLocationCoordinate2D(latitude: route.origin.lat, longitude: route.origin.lon)) {
                    routePin(title: "Origin", systemImage: "location.fill", color: slate)
                }
                Annotation("Destination", coordinate: CLLocationCoordinate2D(latitude: route.destination.lat, longitude: route.destination.lon)) {
                    routePin(title: "Destination", systemImage: "flag.checkered.2.crossed", color: .green)
                }
            } else if let currentCoordinate {
                Annotation("Current", coordinate: currentCoordinate) {
                    routePin(title: "Current", systemImage: "location.north.circle.fill", color: slate)
                }
            }
        }
        .frame(height: 250)
        .clipShape(RoundedRectangle(cornerRadius: 18))
        .overlay(
            RoundedRectangle(cornerRadius: 18)
                .stroke(slate.opacity(0.28), lineWidth: 1)
        )
        .overlay(alignment: .topLeading) {
            HStack(spacing: 8) {
                Label(route == nil ? "Live Map" : "Active Route", systemImage: "map.fill")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(.black.opacity(0.25), in: Capsule())
                Spacer()
                if loadingRoute {
                    ProgressView()
                        .tint(.white)
                        .padding(8)
                        .background(.black.opacity(0.25), in: Circle())
                }
            }
            .padding(14)
        }
    }

    private var plannerCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 10) {
                ZStack {
                    Circle().fill(slate.opacity(0.14)).frame(width: 44, height: 44)
                    Image(systemName: "road.lanes")
                        .font(.system(size: 18))
                        .foregroundStyle(slate)
                }
                VStack(alignment: .leading, spacing: 2) {
                    Text("Route Planner")
                        .font(.title3.bold())
                        .foregroundStyle(.white)
                    Text("Maria Hill · Live route weather")
                        .font(.caption2)
                        .foregroundStyle(slate.opacity(0.78))
                }
                Spacer()
                if loadingLocations {
                    ProgressView().tint(slate)
                }
            }

            Picker("Origin", selection: $selectedOriginMode) {
                ForEach(availableOriginModes) { mode in
                    Text(mode.title).tag(mode)
                }
            }
            .pickerStyle(.segmented)

            VStack(alignment: .leading, spacing: 8) {
                Text(originDescriptor)
                    .font(.caption)
                    .foregroundStyle(.secondary)

                TextField("Where do you want to go?", text: $destinationText)
                    .textInputAutocapitalization(.words)
                    .disableAutocorrection(true)
                    .focused($destinationFocused)
                    .submitLabel(.go)
                    .onSubmit { Task { await planRoute() } }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
                    .background(
                        RoundedRectangle(cornerRadius: 14)
                            .fill(.white.opacity(0.06))
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .stroke(.white.opacity(0.08), lineWidth: 1)
                    )
                    .foregroundStyle(.white)
            }

            HStack(spacing: 10) {
                Button {
                    destinationFocused = false
                    Task { await planRoute() }
                } label: {
                    Label(loadingRoute ? "Planning…" : "Plan Route", systemImage: "point.topleft.down.curvedto.point.bottomright.up")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(slate)
                .disabled(loadingRoute || destinationText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

                if let route {
                    Button {
                        openInAppleMaps(route)
                    } label: {
                        Label("Maps", systemImage: "arrow.triangle.turn.up.right.diamond.fill")
                    }
                    .buttonStyle(.bordered)
                    .tint(.white)
                } else if selectedOriginMode == .current && loc.authorizationStatus == .notDetermined {
                    Button("Use Phone Location") {
                        loc.requestAndFetch(force: true, userInitiated: true)
                    }
                    .buttonStyle(.bordered)
                    .tint(.white)
                }
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 18))
    }

    private var quickDestinationsCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Quick Destinations", systemImage: "star.fill")
                .font(.caption.weight(.semibold))
                .foregroundStyle(slate)

            if !savedLocations.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(savedLocations) { location in
                            Button {
                                selectedSavedLocationID = location.id
                                destinationText = location.address
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(location.label)
                                        .font(.subheadline.weight(.semibold))
                                        .foregroundStyle(.white)
                                    Text(location.geography.isEmpty ? location.address : location.geography)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                        .lineLimit(1)
                                }
                                .padding(.horizontal, 14)
                                .padding(.vertical, 12)
                                .frame(width: 180, alignment: .leading)
                                .background(
                                    RoundedRectangle(cornerRadius: 14)
                                        .fill(location.id == selectedSavedLocationID ? slate.opacity(0.22) : .white.opacity(0.04))
                                )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }

            if !recentDestinations.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Recent")
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.secondary)
                    ForEach(recentDestinations, id: \.self) { destination in
                        Button {
                            destinationText = destination
                        } label: {
                            HStack(spacing: 10) {
                                Image(systemName: "clock.arrow.circlepath")
                                    .foregroundStyle(slate.opacity(0.8))
                                Text(destination)
                                    .font(.subheadline)
                                    .foregroundStyle(.white.opacity(0.86))
                                    .lineLimit(1)
                                Spacer()
                            }
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 18))
    }

    private func routeSummaryCard(_ route: NavigationRouteOverview) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(route.destination.label)
                        .font(.title3.bold())
                        .foregroundStyle(.white)
                        .lineLimit(2)
                    Text(route.origin.label)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
                Spacer()
                Text(route.hazardActive ? "Caution" : "Clear")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(route.hazardActive ? .black : .white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(route.hazardActive ? Color.orange : slate.opacity(0.45), in: Capsule())
            }

            Text(route.summary)
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.84))

            HStack(spacing: 10) {
                routeMetric(icon: "car.fill", title: "Drive", value: route.route.durationMinutes.map { "\($0) min" } ?? "--")
                routeMetric(icon: "road.lanes", title: "Distance", value: route.route.distanceMiles.map { String(format: "%.1f mi", $0) } ?? "--")
                routeMetric(icon: "cloud.sun.fill", title: "Samples", value: "\(route.samples.count)")
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 18))
    }

    private func routeWeatherCard(_ route: NavigationRouteOverview) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Route Weather", systemImage: "cloud.bolt.rain.fill")
                .font(.caption.weight(.semibold))
                .foregroundStyle(slate)

            ForEach(route.samples) { sample in
                HStack(alignment: .top, spacing: 12) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 10)
                            .fill(routeSampleAccent(for: sample).opacity(0.16))
                            .frame(width: 42, height: 42)
                        Image(systemName: routeSampleIcon(for: sample))
                            .foregroundStyle(routeSampleAccent(for: sample))
                    }

                    VStack(alignment: .leading, spacing: 3) {
                        Text(sample.condition.isEmpty ? "Weather sample" : sample.condition)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.white)
                        Text(sample.temperatureF.map { "\(Int($0.rounded()))°" } ?? "--")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        if let rainPct = sample.rainPct, rainPct > 0 {
                            Text("Rain chance \(rainPct)%")
                                .font(.caption2)
                                .foregroundStyle(routeSampleAccent(for: sample))
                        }
                        if !sample.alerts.isEmpty {
                            Text(sample.alerts.joined(separator: " • "))
                                .font(.caption2)
                                .foregroundStyle(.orange.opacity(0.95))
                                .lineLimit(2)
                        }
                    }

                    Spacer()

                    Text(sample.wind.isEmpty ? "--" : sample.wind)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 2)
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 18))
    }

    private func routeErrorCard(_ message: String) -> some View {
        VStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 34))
                .foregroundStyle(.orange)
            Text("Route unavailable")
                .font(.headline)
                .foregroundStyle(.white)
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Try Again") {
                Task { await planRoute() }
            }
            .buttonStyle(.borderedProminent)
            .tint(slate)
        }
        .padding(20)
        .glassEffect(in: RoundedRectangle(cornerRadius: 18))
    }

    private var emptyStateCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("Navigation Intelligence", systemImage: "map.circle.fill")
                .font(.caption.weight(.semibold))
                .foregroundStyle(slate)
            Text("Plan a drive and JARVIS will pull distance, ETA, route weather, and caution points from the live stack.")
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.78))
            Text("Start with a destination above or tap one of your saved places.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 18))
    }

    // MARK: - Helpers

    private var availableOriginModes: [OriginMode] {
        selectedSavedLocation == nil ? [.current] : [.home, .current]
    }

    private var originDescriptor: String {
        switch selectedOriginMode {
        case .home:
            if let selectedSavedLocation {
                return "Starting from \(selectedSavedLocation.label)"
            }
            return "No saved home location available yet."
        case .current:
            if let location = loc.location {
                let lat = String(format: "%.4f", location.coordinate.latitude)
                let lon = String(format: "%.4f", location.coordinate.longitude)
                return "Using phone location \(lat), \(lon)"
            }
            if loc.authorizationStatus == .denied || loc.authorizationStatus == .restricted {
                return "Phone location is disabled. Switch to Home or re-enable Location Services."
            }
            return "Phone location will be used when available."
        }
    }

    private func routeMetric(icon: String, title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Image(systemName: icon)
                .foregroundStyle(slate)
            Text(value)
                .font(.headline.bold())
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .glassEffect(in: RoundedRectangle(cornerRadius: 14))
    }

    private func routePin(title: String, systemImage: String, color: Color) -> some View {
        VStack(spacing: 4) {
            Image(systemName: systemImage)
                .font(.system(size: 16, weight: .bold))
                .foregroundStyle(.white)
                .padding(8)
                .background(color, in: Circle())
            Text(title)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.white)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(.black.opacity(0.3), in: Capsule())
        }
    }

    private func routeSampleAccent(for sample: NavigationRouteSample) -> Color {
        if !sample.alerts.isEmpty { return .orange }
        if let rain = sample.rainPct, rain >= 70 { return .blue }
        let lower = sample.condition.lowercased()
        if lower.contains("storm") || lower.contains("thunder") { return .purple }
        return slate
    }

    private func routeSampleIcon(for sample: NavigationRouteSample) -> String {
        let lower = sample.condition.lowercased()
        if lower.contains("snow") || lower.contains("freez") { return "snowflake"
        }
        if lower.contains("storm") || lower.contains("thunder") { return "cloud.bolt.rain.fill"
        }
        if lower.contains("rain") || lower.contains("shower") { return "cloud.rain.fill"
        }
        if lower.contains("cloud") { return "cloud.fill"
        }
        return "sun.max.fill"
    }

    private func restoreRecentDestinations() {
        recentDestinations = UserDefaults.standard.stringArray(forKey: Self.recentDestinationsKey) ?? []
    }

    private func saveRecentDestination(_ destination: String) {
        let trimmed = destination.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        var next = recentDestinations.filter { $0.caseInsensitiveCompare(trimmed) != .orderedSame }
        next.insert(trimmed, at: 0)
        recentDestinations = Array(next.prefix(5))
        UserDefaults.standard.set(recentDestinations, forKey: Self.recentDestinationsKey)
    }

    private func focusMap(on route: NavigationRouteOverview) {
        if let polyline = routePolyline {
            cameraPosition = .rect(polyline.boundingMapRect)
            return
        }
        let rect = MKMapRect(
            origin: MKMapPoint(CLLocationCoordinate2D(latitude: route.origin.lat, longitude: route.origin.lon)),
            size: MKMapSize(width: 1200, height: 1200)
        )
        cameraPosition = .rect(rect)
    }

    private func openInAppleMaps(_ route: NavigationRouteOverview) {
        let destination = route.destination.label.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? route.destination.label
        let origin = route.origin.label.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? route.origin.label
        guard let url = URL(string: "http://maps.apple.com/?saddr=\(origin)&daddr=\(destination)&dirflg=d") else { return }
        UIApplication.shared.open(url)
    }

    private func loadNavigationLocations() async {
        loadingLocations = true
        defer { loadingLocations = false }
        do {
            let overview = try await AppleAPIClient.shared.fetchNavigationLocations()
            savedLocations = overview.savedLocations
            preferredLocationId = overview.preferredLocationId
            if selectedSavedLocationID == nil {
                selectedSavedLocationID = overview.preferredLocationId ?? overview.savedLocations.first?.id
            }
            if availableOriginModes.contains(selectedOriginMode) == false {
                selectedOriginMode = availableOriginModes.first ?? .current
            }
        } catch {
            routeError = error.localizedDescription
        }
    }

    private func planRoute() async {
        let destination = destinationText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !destination.isEmpty else { return }
        destinationFocused = false
        loadingRoute = true
        routeError = nil
        defer { loadingRoute = false }

        do {
            let origin = try await resolveOriginQuery()
            let overview = try await AppleAPIClient.shared.fetchNavigationRoute(origin: origin, destination: destination)
            route = overview
            focusMap(on: overview)
            saveRecentDestination(destination)
        } catch {
            route = nil
            routeError = error.localizedDescription
        }
    }

    private func resolveOriginQuery() async throws -> String {
        switch selectedOriginMode {
        case .home:
            if let selectedSavedLocation, !selectedSavedLocation.address.isEmpty {
                return selectedSavedLocation.address
            }
            if let coordinate = geo.homeCoordinate {
                return try await reverseGeocodeCoordinate(coordinate)
            }
            throw JarvisClientError.serverError("No saved home location is configured yet.")
        case .current:
            if let coordinate = currentCoordinate {
                return try await reverseGeocodeCoordinate(coordinate)
            }
            throw JarvisClientError.serverError("Phone location is not available yet.")
        }
    }

    private func reverseGeocodeCoordinate(_ coordinate: CLLocationCoordinate2D) async throws -> String {
        let geocoder = CLGeocoder()
        let placemarks = try await geocoder.reverseGeocodeLocation(
            CLLocation(latitude: coordinate.latitude, longitude: coordinate.longitude)
        )
        if let placemark = placemarks.first {
            let parts = [
                placemark.name,
                placemark.locality,
                placemark.administrativeArea,
                placemark.postalCode,
            ]
            .compactMap { value in
                let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                return trimmed.isEmpty ? nil : trimmed
            }
            if !parts.isEmpty {
                return parts.joined(separator: ", ")
            }
        }
        return "\(coordinate.latitude),\(coordinate.longitude)"
    }
}

#Preview {
    NavigateView()
}
