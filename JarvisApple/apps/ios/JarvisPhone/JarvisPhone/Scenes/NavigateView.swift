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
    @ObservedObject private var speech = SpeechRecognitionManager.shared
    @StateObject private var completer = NavigationSearchCompleter()

    @State private var cameraPosition: MapCameraPosition = .automatic
    @State private var destinationText = ""
    @State private var route: NavigationRouteOverview?
    @State private var stopSections: [NavigationStopSection] = []
    @State private var savedLocations: [NavigationSavedLocation] = []
    @State private var preferredLocationId: String?
    @State private var favoriteDestinations: [String] = []
    @State private var recentDestinations: [String] = []
    @State private var activeStopCategoryIDs: Set<String> = ["food", "starbucks", "parks", "historic", "family"]
    @State private var selectedOriginMode: OriginMode = .home
    @State private var loadingRoute = false
    @State private var loadingStops = false
    @State private var loadingLocations = false
    @State private var routeError: String?
    @State private var selectedSavedLocationID: String?
    @FocusState private var destinationFocused: Bool

    private let slate = Color(red: 0.4, green: 0.55, blue: 0.75)
    private static let favoriteDestinationsKey = "jarvis.navigate.favoriteDestinations"
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

    private var leadingRouteSample: NavigationRouteSample? {
        route?.samples.first
    }

    private var upcomingSteps: [NavigationRouteStep] {
        Array(route?.route.steps.prefix(4) ?? [])
    }

    private var arrivalTimeText: String? {
        guard let minutes = route?.route.durationMinutes else { return nil }
        let arrival = Date().addingTimeInterval(TimeInterval(minutes * 60))
        return arrival.formatted(date: .omitted, time: .shortened)
    }

    private var visibleStopSections: [NavigationStopSection] {
        let visible = stopSections.filter { section in
            guard section.items.isEmpty == false else { return false }
            return activeStopCategoryIDs.contains(section.id)
        }
        return visible.isEmpty ? stopSections.filter { !$0.items.isEmpty } : visible
    }

    private var activeStopSummary: String {
        let labels = stopSections
            .filter { activeStopCategoryIDs.contains($0.id) && !$0.items.isEmpty }
            .map(\.label)

        guard labels.isEmpty == false else {
            return "JARVIS is ready to surface coffee, food, parks, historic sites, family stops, and gas along the route."
        }
        return "Showing \(labels.joined(separator: ", ")) stops from JARVIS route intelligence."
    }

    private var routePolyline: MKPolyline? {
        let coordinates = route?.route.coordinates.compactMap { pair -> CLLocationCoordinate2D? in
            guard pair.count == 2 else { return nil }
            return CLLocationCoordinate2D(latitude: pair[1], longitude: pair[0])
        } ?? []
        guard !coordinates.isEmpty else { return nil }
        return MKPolyline(coordinates: coordinates, count: coordinates.count)
    }

    private var destinationSuggestions: [DestinationSuggestion] {
        if destinationText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return historyAndFavoriteSuggestions
        }

        let live = completer.results.map(DestinationSuggestion.init(completion:))
        if !live.isEmpty {
            return live
        }

        let query = destinationText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return [] }

        let fallback = (favoriteDestinations + recentDestinations)
            .filter { $0.localizedCaseInsensitiveContains(query) }
            .prefix(6)
            .map(DestinationSuggestion.init(fallbackTitle:))
        return Array(fallback)
    }

    private var showSuggestions: Bool {
        destinationFocused && !destinationSuggestions.isEmpty
    }

    private var historyAndFavoriteSuggestions: [DestinationSuggestion] {
        var results: [DestinationSuggestion] = []
        results.append(contentsOf: favoriteDestinations.prefix(3).map(DestinationSuggestion.init(favoriteTitle:)))
        let filteredRecent = recentDestinations.filter { recent in
            favoriteDestinations.contains { $0.caseInsensitiveCompare(recent) == .orderedSame } == false
        }
        results.append(contentsOf: filteredRecent.prefix(5).map(DestinationSuggestion.init(recentTitle:)))
        return results
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
                            routeGuidanceCard(route)
                            if !upcomingSteps.isEmpty {
                                routeStepsCard
                            }
                            routeSummaryCard(route)
                            routeStopsCard
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
            restoreFavoriteDestinations()
            restoreRecentDestinations()
            await loadNavigationLocations()
            loc.requestAndFetch()
        }
        .onChange(of: destinationText) { _, newValue in
            completer.update(query: newValue)
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
        .overlay(alignment: .bottomTrailing) {
            VStack(spacing: 10) {
                if route != nil {
                    Button {
                        focusMapOnCurrentContext()
                    } label: {
                        Image(systemName: "map")
                            .font(.system(size: 16, weight: .semibold))
                            .frame(width: 40, height: 40)
                    }
                    .buttonStyle(.plain)
                    .background(.black.opacity(0.28), in: Circle())
                    .foregroundStyle(.white)
                }

                Button {
                    centerMapOnUser()
                } label: {
                    Image(systemName: "location.fill")
                        .font(.system(size: 16, weight: .semibold))
                        .frame(width: 40, height: 40)
                }
                .buttonStyle(.plain)
                .background(.black.opacity(0.28), in: Circle())
                .foregroundStyle(.white)
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

                HStack(spacing: 10) {
                    TextField("Where do you want to go?", text: $destinationText)
                        .textInputAutocapitalization(.words)
                        .disableAutocorrection(true)
                        .focused($destinationFocused)
                        .submitLabel(.go)
                        .onSubmit { Task { await planRoute() } }
                        .foregroundStyle(.white)

                    Button {
                        toggleDestinationListening()
                    } label: {
                        Image(systemName: speech.isListening ? "stop.fill" : "mic.fill")
                            .font(.system(size: 16, weight: .semibold))
                            .frame(width: 34, height: 34)
                            .foregroundStyle(.white)
                            .background((speech.isListening ? slate : Color.white.opacity(0.08)), in: Circle())
                    }
                    .buttonStyle(.plain)
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 12)
                .background(
                    RoundedRectangle(cornerRadius: 14)
                        .fill(.white.opacity(0.06))
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(speech.isListening ? slate.opacity(0.55) : .white.opacity(0.08), lineWidth: 1)
                )

                if speech.isListening || !speech.transcript.isEmpty || speech.errorMessage != nil {
                    navigationVoiceStatus
                }
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
                    Button {
                        toggleFavorite(route.destination.label)
                    } label: {
                        Image(systemName: isFavoriteDestination(route.destination.label) ? "star.fill" : "star")
                    }
                    .buttonStyle(.bordered)
                    .tint(isFavoriteDestination(route.destination.label) ? .yellow : .white)
                } else if selectedOriginMode == .current && loc.authorizationStatus == .notDetermined {
                    Button("Use Phone Location") {
                        loc.requestAndFetch(force: true, userInitiated: true)
                    }
                    .buttonStyle(.bordered)
                    .tint(.white)
                }
            }

            if selectedOriginMode == .current && selectedSavedLocation != nil {
                Button {
                    if let homeAddress = selectedSavedLocation?.address {
                        destinationText = homeAddress
                        destinationFocused = false
                        Task { await planRoute() }
                    }
                } label: {
                    Label("Route Home", systemImage: "house.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(.white)
            }

            if showSuggestions {
                destinationSuggestionsCard
            }

            if route != nil {
                Button(role: .destructive) {
                    clearRoute()
                } label: {
                    Label("End Route", systemImage: "xmark.circle.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(.red)
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

            if !favoriteDestinations.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Favorites")
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.secondary)
                    ForEach(favoriteDestinations, id: \.self) { destination in
                        Button {
                            queueDestination(destination, autoPlan: true)
                        } label: {
                            HStack(spacing: 10) {
                                Image(systemName: "star.fill")
                                    .foregroundStyle(.yellow)
                                Text(destination)
                                    .font(.subheadline)
                                    .foregroundStyle(.white.opacity(0.9))
                                    .lineLimit(1)
                                Spacer()
                            }
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            if !savedLocations.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(savedLocations) { location in
                            Button {
                                selectedSavedLocationID = location.id
                                queueDestination(location.address, autoPlan: true)
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
                            queueDestination(destination, autoPlan: true)
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

    private var navigationVoiceStatus: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: speech.isListening ? "waveform" : "mic.slash.fill")
                .foregroundStyle(speech.isListening ? slate : .orange)
                .symbolEffect(.variableColor.iterative, isActive: speech.isListening)
                .padding(.top, 2)
            VStack(alignment: .leading, spacing: 3) {
                if speech.isListening {
                    Text("Listening for your destination…")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white)
                    if !speech.transcript.isEmpty {
                        Text(speech.transcript)
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.75))
                    }
                } else if let error = speech.errorMessage, !error.isEmpty {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.orange.opacity(0.95))
                } else if !speech.transcript.isEmpty {
                    Text("Captured destination")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white)
                    Text(speech.transcript)
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.75))
                }
            }
            Spacer()
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(.white.opacity(0.04))
        )
    }

    private func routeGuidanceCard(_ route: NavigationRouteOverview) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Label("Drive Status", systemImage: "location.north.line.fill")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(slate)
                    Text(route.destination.label)
                        .font(.title3.bold())
                        .foregroundStyle(.white)
                        .lineLimit(2)
                }
                Spacer()
                if let arrivalTimeText {
                    VStack(alignment: .trailing, spacing: 2) {
                        Text("ETA")
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(.secondary)
                        Text(arrivalTimeText)
                            .font(.headline.bold())
                            .foregroundStyle(.white)
                    }
                }
            }

            if let sample = leadingRouteSample {
                HStack(spacing: 10) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 12)
                            .fill(routeSampleAccent(for: sample).opacity(0.15))
                            .frame(width: 48, height: 48)
                        Image(systemName: routeSampleIcon(for: sample))
                            .foregroundStyle(routeSampleAccent(for: sample))
                    }

                    VStack(alignment: .leading, spacing: 3) {
                        Text(primaryGuidanceTitle(sample: sample))
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.white)
                        Text(primaryGuidanceSubtitle(route: route, sample: sample))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        if !sample.alerts.isEmpty {
                            Text(sample.alerts.prefix(2).joined(separator: " • "))
                                .font(.caption2)
                                .foregroundStyle(.orange.opacity(0.95))
                                .lineLimit(2)
                        }
                    }
                    Spacer()
                }
            } else {
                Text(route.summary)
                    .font(.subheadline)
                    .foregroundStyle(.white.opacity(0.84))
            }

            HStack(spacing: 10) {
                routeMetric(icon: "clock.fill", title: "Arrival", value: arrivalTimeText ?? "--")
                routeMetric(icon: "thermometer.medium", title: "Temp", value: leadingRouteSample?.temperatureF.map { "\(Int($0.rounded()))°" } ?? "--")
                routeMetric(icon: "exclamationmark.triangle.fill", title: "Alerts", value: alertCountLabel)
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 18))
    }

    private var routeStepsCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Upcoming Maneuvers", systemImage: "arrow.triangle.turn.up.right.diamond.fill")
                .font(.caption.weight(.semibold))
                .foregroundStyle(slate)

            ForEach(upcomingSteps) { step in
                HStack(alignment: .top, spacing: 12) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 10)
                            .fill(stepAccentColor(for: step).opacity(0.15))
                            .frame(width: 40, height: 40)
                        Image(systemName: stepIcon(for: step))
                            .foregroundStyle(stepAccentColor(for: step))
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        Text(step.instruction.isEmpty ? "Continue on route" : step.instruction)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.white)
                            .fixedSize(horizontal: false, vertical: true)
                        Text(stepMetaLine(step))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()

                    Text("#\(step.sequence)")
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(.white.opacity(0.7))
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
                routeMetric(icon: "mappin.and.ellipse", title: "Stops", value: stopCountLabel)
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 18))
    }

    private var routeStopsCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("Along The Way", systemImage: "map.circle.fill")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(slate)
                Spacer()
                if loadingStops {
                    ProgressView().tint(slate)
                }
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(stopSections.filter { !$0.items.isEmpty }) { section in
                        let isActive = activeStopCategoryIDs.contains(section.id)
                        Button {
                            toggleStopCategory(section.id)
                        } label: {
                            HStack(spacing: 8) {
                                Image(systemName: stopSectionIcon(for: section))
                                    .foregroundStyle(isActive ? .black : stopSectionColor(for: section))
                                Text(section.label)
                                    .font(.caption.weight(.semibold))
                                Text("\(section.items.count)")
                                    .font(.caption2.weight(.bold))
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background((isActive ? Color.black.opacity(0.12) : stopSectionColor(for: section).opacity(0.18)), in: Capsule())
                            }
                            .foregroundStyle(isActive ? .black : .white.opacity(0.86))
                            .padding(.horizontal, 12)
                            .padding(.vertical, 9)
                            .background(
                                Capsule()
                                    .fill(isActive ? stopSectionColor(for: section) : .white.opacity(0.06))
                            )
                            .overlay(
                                Capsule()
                                    .stroke(isActive ? stopSectionColor(for: section) : .white.opacity(0.08), lineWidth: 1)
                            )
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            Text(activeStopSummary)
                .font(.caption)
                .foregroundStyle(.secondary)

            if stopSections.allSatisfy({ $0.items.isEmpty }) {
                Text("No suggested stops surfaced yet for this route.")
                    .font(.subheadline)
                    .foregroundStyle(.white.opacity(0.76))
            } else {
                ForEach(visibleStopSections) { section in
                    VStack(alignment: .leading, spacing: 10) {
                        HStack(spacing: 8) {
                            Image(systemName: stopSectionIcon(for: section))
                                .foregroundStyle(stopSectionColor(for: section))
                            Text(section.label)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(.white)
                            Text("\(section.items.count)")
                                .font(.caption2.weight(.bold))
                                .foregroundStyle(.black)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 3)
                                .background(stopSectionColor(for: section), in: Capsule())
                        }

                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 10) {
                                ForEach(section.items.prefix(8)) { stop in
                                    NavigationStopCard(
                                        stop: stop,
                                        color: stopSectionColor(for: section),
                                        icon: stopSectionIcon(for: section),
                                        onRouteHere: {
                                            routeToStop(stop)
                                        },
                                        onOpenInMaps: {
                                            openStopInAppleMaps(stop)
                                        }
                                    )
                                }
                            }
                        }
                    }
                }
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

    private var destinationSuggestionsCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Suggestions")
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.secondary)

            ForEach(destinationSuggestions) { suggestion in
                Button {
                    selectSuggestion(suggestion)
                } label: {
                    HStack(alignment: .top, spacing: 10) {
                        Image(systemName: suggestion.symbolName)
                            .foregroundStyle(suggestion.tintColor(slate: slate))
                            .padding(.top, 2)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(suggestion.title)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(.white)
                                .lineLimit(1)
                            if !suggestion.subtitle.isEmpty {
                                Text(suggestion.subtitle)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                        }
                        Spacer()
                    }
                }
                .buttonStyle(.plain)
            }
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(.white.opacity(0.05))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(.white.opacity(0.08), lineWidth: 1)
        )
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

    private var stopCountLabel: String {
        let count = stopSections.reduce(0) { $0 + $1.items.count }
        return count == 0 ? "--" : "\(count)"
    }

    private var alertCountLabel: String {
        let count = route?.samples.reduce(0) { $0 + $1.alerts.count } ?? 0
        return count == 0 ? "0" : "\(count)"
    }

    private func stopSectionColor(for section: NavigationStopSection) -> Color {
        switch section.id {
        case "food": return .orange
        case "starbucks": return Color(red: 0.0, green: 0.44, blue: 0.29)
        case "parks": return .green
        case "historic": return .yellow
        case "family": return .blue
        case "gas": return .gray
        default: return slate
        }
    }

    private func stopSectionIcon(for section: NavigationStopSection) -> String {
        switch section.id {
        case "food": return "fork.knife"
        case "starbucks": return "cup.and.saucer.fill"
        case "parks": return "tree.fill"
        case "historic": return "building.columns.fill"
        case "family": return "figure.2.and.child.holdinghands"
        case "gas": return "fuelpump.fill"
        default: return "mappin.circle.fill"
        }
    }

    private func restoreRecentDestinations() {
        recentDestinations = UserDefaults.standard.stringArray(forKey: Self.recentDestinationsKey) ?? []
    }

    private func restoreFavoriteDestinations() {
        favoriteDestinations = UserDefaults.standard.stringArray(forKey: Self.favoriteDestinationsKey) ?? []
    }

    private func saveRecentDestination(_ destination: String) {
        let trimmed = destination.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        var next = recentDestinations.filter { $0.caseInsensitiveCompare(trimmed) != .orderedSame }
        next.insert(trimmed, at: 0)
        recentDestinations = Array(next.prefix(5))
        UserDefaults.standard.set(recentDestinations, forKey: Self.recentDestinationsKey)
    }

    private func toggleFavorite(_ destination: String) {
        let trimmed = destination.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        if let index = favoriteDestinations.firstIndex(where: { $0.caseInsensitiveCompare(trimmed) == .orderedSame }) {
            favoriteDestinations.remove(at: index)
        } else {
            favoriteDestinations.insert(trimmed, at: 0)
            favoriteDestinations = Array(favoriteDestinations.prefix(8))
        }
        UserDefaults.standard.set(favoriteDestinations, forKey: Self.favoriteDestinationsKey)
    }

    private func isFavoriteDestination(_ destination: String) -> Bool {
        favoriteDestinations.contains { $0.caseInsensitiveCompare(destination) == .orderedSame }
    }

    private func selectSuggestion(_ suggestion: DestinationSuggestion) {
        queueDestination(suggestion.displayText, autoPlan: false)
    }

    private func queueDestination(_ destination: String, autoPlan: Bool) {
        let trimmed = destination.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        destinationText = trimmed
        destinationFocused = false
        guard autoPlan else { return }
        Task { await planRoute() }
    }

    private func toggleDestinationListening() {
        if speech.isListening {
            speech.stopListening()
            return
        }

        if !speech.isAuthorized {
            Task { await speech.checkAuthorization() }
        }

        speech.startListening { text in
            Task { @MainActor in
                let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
                guard !trimmed.isEmpty else { return }
                destinationText = trimmed
                destinationFocused = false
            }
        }
    }

    private func clearRoute() {
        route = nil
        stopSections = []
        routeError = nil
        cameraPosition = .automatic
    }

    private func toggleStopCategory(_ categoryID: String) {
        if activeStopCategoryIDs.contains(categoryID) {
            let remaining = activeStopCategoryIDs.subtracting([categoryID])
            if remaining.isEmpty == false {
                activeStopCategoryIDs = remaining
            }
        } else {
            activeStopCategoryIDs.insert(categoryID)
        }
    }

    private func routeToStop(_ stop: NavigationStop) {
        let destination = [stop.name, stop.address]
            .filter { !$0.isEmpty }
            .joined(separator: ", ")
        queueDestination(destination, autoPlan: true)
    }

    private func openStopInAppleMaps(_ stop: NavigationStop) {
        let query = [stop.name, stop.address]
            .filter { !$0.isEmpty }
            .joined(separator: " ")
            .addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? stop.name
        guard let url = URL(string: "http://maps.apple.com/?q=\(query)") else { return }
        UIApplication.shared.open(url)
    }

    private func centerMapOnUser() {
        if let currentCoordinate {
            cameraPosition = .region(
                MKCoordinateRegion(
                    center: currentCoordinate,
                    span: MKCoordinateSpan(latitudeDelta: 0.08, longitudeDelta: 0.08)
                )
            )
        } else if selectedOriginMode == .current {
            loc.requestAndFetch(force: true, userInitiated: true)
        }
    }

    private func focusMapOnCurrentContext() {
        if let route {
            focusMap(on: route)
        } else {
            centerMapOnUser()
        }
    }

    private func guidanceSecondaryLine(for route: NavigationRouteOverview, sample: NavigationRouteSample) -> String {
        var parts: [String] = []
        if let minutes = route.route.durationMinutes {
            parts.append("\(minutes) min drive")
        }
        if let miles = route.route.distanceMiles {
            parts.append(String(format: "%.1f mi", miles))
        }
        if let rain = sample.rainPct, rain > 0 {
            parts.append("Rain \(rain)%")
        }
        if !sample.wind.isEmpty {
            parts.append(sample.wind)
        }
        return parts.isEmpty ? route.summary : parts.joined(separator: " • ")
    }

    private func primaryGuidanceTitle(sample: NavigationRouteSample) -> String {
        if let firstStep = route?.route.steps.first, !firstStep.instruction.isEmpty {
            return firstStep.instruction
        }
        return sample.condition.isEmpty ? "Conditions ahead are updating" : sample.condition
    }

    private func primaryGuidanceSubtitle(route: NavigationRouteOverview, sample: NavigationRouteSample) -> String {
        if let firstStep = route.route.steps.first {
            return stepMetaLine(firstStep)
        }
        return guidanceSecondaryLine(for: route, sample: sample)
    }

    private func stepMetaLine(_ step: NavigationRouteStep) -> String {
        var parts: [String] = []
        if let miles = step.distanceMiles {
            parts.append(String(format: "%.1f mi", miles))
        }
        if let minutes = step.durationMinutes {
            parts.append("\(minutes) min")
        }
        if !step.name.isEmpty {
            parts.append(step.name)
        }
        return parts.isEmpty ? "Stay on route" : parts.joined(separator: " • ")
    }

    private func stepIcon(for step: NavigationRouteStep) -> String {
        let maneuver = step.maneuver.lowercased()
        let modifier = step.modifier.lowercased()
        if maneuver.contains("arrive") { return "flag.checkered.2.crossed" }
        if modifier.contains("left") { return "arrow.turn.up.left" }
        if modifier.contains("right") { return "arrow.turn.up.right" }
        if maneuver.contains("roundabout") || maneuver.contains("rotary") { return "arrow.trianglehead.clockwise" }
        if maneuver.contains("merge") || maneuver.contains("fork") { return "arrow.merge" }
        if maneuver.contains("depart") { return "car.fill" }
        return "arrow.up"
    }

    private func stepAccentColor(for step: NavigationRouteStep) -> Color {
        let modifier = step.modifier.lowercased()
        let maneuver = step.maneuver.lowercased()
        if maneuver.contains("arrive") { return .green }
        if modifier.contains("left") { return .orange }
        if modifier.contains("right") { return .blue }
        return slate
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
            if let home = overview.savedLocations.first(where: { $0.id == overview.preferredLocationId }) ?? overview.savedLocations.first,
               let latitude = home.latitude,
               let longitude = home.longitude {
                geo.syncHomeCoordinate(latitude: latitude, longitude: longitude)
            }
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
            await loadStops(origin: origin, destination: destination)
            saveRecentDestination(destination)
        } catch {
            route = nil
            stopSections = []
            routeError = error.localizedDescription
        }
    }

    private func loadStops(origin: String, destination: String) async {
        loadingStops = true
        defer { loadingStops = false }
        do {
            let overview = try await AppleAPIClient.shared.fetchNavigationStops(origin: origin, destination: destination)
            stopSections = overview.sections
        } catch {
            stopSections = []
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

private struct DestinationSuggestion: Identifiable {
    private enum Kind {
        case live
        case favorite
        case recent
        case fallback
    }

    let id: String
    let title: String
    let subtitle: String
    private let kind: Kind

    init(completion: MKLocalSearchCompletion) {
        self.title = completion.title
        self.subtitle = completion.subtitle
        self.kind = .live
        self.id = [completion.title, completion.subtitle].joined(separator: "::")
    }

    init(fallbackTitle: String) {
        self.id = fallbackTitle
        self.title = fallbackTitle
        self.subtitle = ""
        self.kind = .fallback
    }

    init(favoriteTitle: String) {
        self.id = "favorite::\(favoriteTitle)"
        self.title = favoriteTitle
        self.subtitle = "Favorite"
        self.kind = .favorite
    }

    init(recentTitle: String) {
        self.id = "recent::\(recentTitle)"
        self.title = recentTitle
        self.subtitle = "Recent"
        self.kind = .recent
    }

    var displayText: String {
        [title, subtitle]
            .filter { part in
                guard !part.isEmpty else { return false }
                return part != "Favorite" && part != "Recent"
            }
            .joined(separator: ", ")
    }

    var symbolName: String {
        switch kind {
        case .live: return "magnifyingglass"
        case .favorite: return "star.fill"
        case .recent, .fallback: return "clock.arrow.circlepath"
        }
    }

    func tintColor(slate: Color) -> Color {
        switch kind {
        case .favorite: return .yellow
        case .recent, .fallback: return slate.opacity(0.8)
        case .live: return slate
        }
    }
}

@MainActor
private final class NavigationSearchCompleter: NSObject, ObservableObject, @preconcurrency MKLocalSearchCompleterDelegate {
    @Published private(set) var results: [MKLocalSearchCompletion] = []

    private let completer = MKLocalSearchCompleter()

    override init() {
        super.init()
        completer.delegate = self
        completer.resultTypes = [.address, .pointOfInterest]
    }

    func update(query: String) {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 2 else {
            results = []
            completer.queryFragment = ""
            return
        }
        completer.queryFragment = trimmed
    }

    func completerDidUpdateResults(_ completer: MKLocalSearchCompleter) {
        results = Array(completer.results.prefix(6))
    }

    func completer(_ completer: MKLocalSearchCompleter, didFailWithError error: Error) {
        results = []
    }
}

private struct NavigationStopCard: View {
    let stop: NavigationStop
    let color: Color
    let icon: String
    let onRouteHere: () -> Void
    let onOpenInMaps: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top) {
                Image(systemName: icon)
                    .foregroundStyle(color)
                Spacer()
                if let marker = stop.routeMileMarker {
                    Text("mi \(Int(marker.rounded()))")
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.secondary)
                }
            }

            Text(stop.name)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.white)
                .lineLimit(2)
            if !stop.address.isEmpty {
                Text(stop.address)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
            if !stop.description.isEmpty {
                Text(stop.description)
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.72))
                    .lineLimit(3)
            }

            HStack(spacing: 8) {
                if let rating = stop.rating {
                    Label(String(format: "%.1f", rating), systemImage: "star.fill")
                        .foregroundStyle(color)
                }
                if let distance = stop.distanceFromRoute {
                    Text("\(String(format: "%.1f", distance)) mi off route")
                        .foregroundStyle(.secondary)
                }
            }
            .font(.caption2)

            HStack(spacing: 8) {
                Button("Route Here") {
                    onRouteHere()
                }
                .buttonStyle(.borderedProminent)
                .tint(color)

                Button("Maps") {
                    onOpenInMaps()
                }
                .buttonStyle(.bordered)
                .tint(.white)
            }
            .font(.caption.weight(.semibold))
        }
        .frame(width: 220, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

#Preview {
    NavigateView()
}
