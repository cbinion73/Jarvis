import SwiftUI
import MapKit
import CoreLocation
import UIKit
import JarvisKit

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

    private enum PanelMode: String, CaseIterable, Identifiable {
        case overview
        case stops
        case settings
        case voice

        var id: String { rawValue }

        var title: String {
            switch self {
            case .overview: return "Overview"
            case .stops: return "Smart Stops"
            case .settings: return "Route Intel"
            case .voice: return "Voice"
            }
        }

        var systemImage: String {
            switch self {
            case .overview: return "point.bottomleft.forward.to.point.topright.scurvepath"
            case .stops: return "sparkles"
            case .settings: return "slider.horizontal.3"
            case .voice: return "waveform"
            }
        }
    }

    private enum StopRailMode {
        case list
        case detail
    }

    private struct PhoneCategoryTile: Identifiable {
        let id: String
        let title: String
        let icon: String
        let color: Color
    }

    private struct SharePayload: Identifiable {
        let id = UUID()
        let text: String
    }

    private struct StoryboardStage: Identifiable {
        let id: String
        let number: String
        let title: String
        let detail: String
        let accent: Color
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
    @State private var routeHistory: [NavigationRouteHistoryEntry] = []
    @State private var activeStopCategoryIDs: Set<String> = ["food", "starbucks", "parks", "historic", "family"]
    @State private var parksHistoricRadiusMiles = 25.0
    @State private var selectedOriginMode: OriginMode = .home
    @State private var loadingRoute = false
    @State private var loadingStops = false
    @State private var loadingLocations = false
    @State private var routeError: String?
    @State private var selectedSavedLocationID: String?
    @State private var currentRouteOriginQuery = ""
    @State private var currentRouteDestinationQuery = ""
    @State private var pendingRouteRestore: NavigationLastRoute?
    @State private var restoringRoute = false
    @State private var panelMode: PanelMode = .overview
    @State private var showPlannerHomeWhileRouteActive = true
    @State private var selectedStopCategoryID = "starbucks"
    @State private var selectedStopID: String?
    @State private var selectedLookAroundScene: MKLookAroundScene?
    @State private var routeLookAroundScene: MKLookAroundScene?
    @State private var stopRailMode: StopRailMode = .list
    @State private var sharePayload: SharePayload?
    @FocusState private var destinationFocused: Bool

    private let slate = Color(red: 0.41, green: 0.56, blue: 0.79)
    private let stopGreen = Color(red: 0.26, green: 0.82, blue: 0.36)
    private let cardFill = Color.white.opacity(0.045)
    private let phoneTiles: [PhoneCategoryTile] = [
        .init(id: "starbucks", title: "Starbucks", icon: "cup.and.saucer.fill", color: Color(red: 0.0, green: 0.44, blue: 0.29)),
        .init(id: "food", title: "Food", icon: "fork.knife", color: .orange),
        .init(id: "parks", title: "Parks", icon: "tree.fill", color: .green),
        .init(id: "historic", title: "Historic", icon: "building.columns.fill", color: .purple),
        .init(id: "family", title: "Family", icon: "heart.fill", color: .pink),
        .init(id: "gas", title: "Gas", icon: "fuelpump.fill", color: .blue),
        .init(id: "more", title: "More", icon: "ellipsis", color: Color.white.opacity(0.8))
    ]

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

    private var primaryStep: NavigationRouteStep? {
        route?.route.steps.first
    }

    private var upcomingSteps: [NavigationRouteStep] {
        Array(route?.route.steps.dropFirst().prefix(3) ?? [])
    }

    private var arrivalTimeText: String? {
        guard let minutes = route?.route.durationMinutes else { return nil }
        let arrival = Date().addingTimeInterval(TimeInterval(minutes * 60))
        return arrival.formatted(date: .omitted, time: .shortened)
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

    private var allVisibleSections: [NavigationStopSection] {
        let filtered = stopSections.filter { !$0.items.isEmpty }
        return filtered.isEmpty ? stopSections : filtered
    }

    private var selectedStopSection: NavigationStopSection? {
        if let matched = allVisibleSections.first(where: { $0.id == selectedStopCategoryID }) {
            return matched
        }
        return allVisibleSections.first
    }

    private var selectedStop: NavigationStop? {
        if let selectedStopID,
           let matched = allVisibleSections.flatMap(\.items).first(where: { $0.id == selectedStopID }) {
            return matched
        }
        return selectedStopSection?.items.first
    }

    private var displayedStops: [NavigationStop] {
        Array(selectedStopSection?.items.prefix(6) ?? [])
    }

    private var mapStops: [NavigationStop] {
        Array(allVisibleSections.flatMap(\.items).prefix(10))
    }

    private var stopPanelSummary: String {
        guard let section = selectedStopSection else {
            return "JARVIS will surface route-aware coffee, food, parks, historic sites, family stops, and gas once the drive is active."
        }
        return "Showing \(section.label.lowercased()) choices ranked from your live route."
    }

    private var trafficHeadline: String {
        if (route?.samples.contains { !$0.alerts.isEmpty } ?? false) {
            return "Moderate"
        }
        return "Light"
    }

    private var trafficDetail: String {
        let alertCount = route?.samples.reduce(0) { $0 + $1.alerts.count } ?? 0
        return alertCount == 0 ? "No incidents on route" : "\(alertCount) route alerts detected"
    }

    private var voicePromptText: String {
        if speech.isListening {
            return speech.transcript.isEmpty ? "Listening for your next route question..." : speech.transcript
        }
        let trimmed = destinationText.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? "Where is the next Starbucks?" : trimmed
    }

    private var voiceResponseText: String {
        guard let stop = selectedStop ?? displayedStops.first else {
            return "I can help find smart stops, route timing, coffee, food, parks, and historic sites along your trip."
        }
        let address = stop.address.isEmpty ? "along your route" : stop.address
        let milesOffRoute = stop.distanceFromRoute.map { String(format: "%.1f", $0) } ?? "0.2"
        let etaImpact = etaImpactLabel(for: stop).replacingOccurrences(of: "+", with: "")
        return "The next \(stop.name) is \(milesOffRoute) miles off your route, at \(address). It will add about \(etaImpact) to your trip."
    }

    private var voiceFollowupQuestion: String {
        if route != nil {
            return "Should we leave now?"
        }
        return "Can you plan that route?"
    }

    private var voiceFollowupAnswer: String {
        if let arrivalTimeText {
            return "Yes, leaving now gets you there by \(arrivalTimeText) with \(trafficHeadline.lowercased()) traffic and no major delays."
        }
        return "Yes. I can plan the route and keep watching traffic, weather, and smart stops."
    }

    private var leaveByHeadline: String {
        guard let minutes = route?.route.durationMinutes else { return "--" }
        let leaveBy = Date().addingTimeInterval(TimeInterval(max(0, minutes - 15) * 60))
        return "Leave by \(leaveBy.formatted(date: .omitted, time: .shortened))"
    }

    private var leaveByDetail: String {
        guard let arrivalTimeText else { return "Best departure estimate" }
        return "Arrive \(arrivalTimeText)"
    }

    private var weatherHeadline: String {
        if let sample = leadingRouteSample {
            return sample.condition.isEmpty ? "Clear" : sample.condition
        }
        return "Clear"
    }

    private var weatherDetail: String {
        if let temp = leadingRouteSample?.temperatureF {
            return "\(Int(temp.rounded())) degrees along your route"
        }
        return "No significant weather delays expected"
    }

    private var timingRiskHeadline: String {
        let count = route?.samples.reduce(0) { $0 + $1.alerts.count } ?? 0
        return count > 1 ? "Medium" : "Low"
    }

    private var timingRiskDetail: String {
        let count = route?.samples.reduce(0) { $0 + $1.alerts.count } ?? 0
        return count > 1 ? "Small delay risk on this route" : "No major delays expected"
    }

    private var routeAlertLines: [String] {
        guard let route else { return [] }
        let alerts = route.samples
            .flatMap(\.alerts)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        var seen = Set<String>()
        return alerts.filter { seen.insert($0).inserted }
    }

    private var weatherSamplePreview: [NavigationRouteSample] {
        Array(route?.samples.prefix(3) ?? [])
    }

    private var familyTravelHeadline: String {
        "All good for the trip"
    }

    private var familyTravelDetail: String {
        if activeStopCategoryIDs.contains("family") {
            return "Family stops and normal traffic are available"
        }
        return "Gas, stops, and route timing look normal"
    }

    private var phoneStoryboardStages: [StoryboardStage] {
        [
            StoryboardStage(
                id: "planner",
                number: "1",
                title: "Planner",
                detail: route == nil ? "Search and launch a route." : "Saved places and recents stay live.",
                accent: slate
            ),
            StoryboardStage(
                id: "route",
                number: "2",
                title: route == nil ? "Active Route" : "On Route",
                detail: "ETA, traffic, and current travel posture.",
                accent: .white.opacity(0.82)
            ),
            StoryboardStage(
                id: "stops",
                number: "3",
                title: "Smart Stops",
                detail: "Coffee, food, parks, and family-fit options.",
                accent: stopGreen
            ),
            StoryboardStage(
                id: "detail",
                number: "4",
                title: "Stop Detail",
                detail: "Detour cost and route-fit before you commit.",
                accent: .orange
            ),
            StoryboardStage(
                id: "intel",
                number: "5",
                title: "Route Intel",
                detail: "Weather, timing risk, and traffic outlook.",
                accent: .cyan
            ),
            StoryboardStage(
                id: "voice",
                number: "6",
                title: "Voice",
                detail: "Hands-free route questions and guidance.",
                accent: .pink
            ),
        ]
    }

    @ViewBuilder
    private var routeRecommendationCard: some View {
        if let route, let stop = allVisibleSections.first?.items.first {
            VStack(alignment: .leading, spacing: 10) {
                Text("JARVIS Recommends")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.72))
                Text(stop.name)
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white)
                Text(route.destination.label)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                HStack {
                    Text(etaImpactLabel(for: stop))
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(stopGreen)
                    Spacer()
                    Text(route.route.distanceMiles.map { String(format: "%.0f mi", $0) } ?? "--")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(16)
            .background(cardFill, in: RoundedRectangle(cornerRadius: 20))
        }
    }

    var body: some View {
        GeometryReader { proxy in
            NavigationStack {
                ZStack {
                    Color.black.ignoresSafeArea()
                    cockpitLayout(size: proxy.size)
                }
                .navigationBarHidden(true)
            }
        }
        .task {
            await loadNavigationLocations()
            loc.requestAndFetch()
        }
        .onChange(of: loc.location) { _, _ in
            guard selectedOriginMode == .current else { return }
            Task { await restorePendingRouteIfPossible() }
        }
        .onChange(of: destinationText) { _, newValue in
            completer.update(query: newValue)
        }
        .onChange(of: selectedOriginMode) { _, newValue in
            persistNavigationState(selectedOriginMode: newValue.rawValue)
            Task { await restorePendingRouteIfPossible() }
        }
        .onChange(of: selectedSavedLocationID) { _, newValue in
            persistNavigationState(selectedSavedLocationID: newValue ?? "")
            Task { await restorePendingRouteIfPossible() }
        }
        .onChange(of: selectedStopCategoryID) { _, _ in
            syncStopSelection()
            stopRailMode = .list
        }
        .onChange(of: selectedStopID) { _, _ in
            Task { await refreshSelectedStopScene() }
        }
    }

    @ViewBuilder
    private func cockpitLayout(size: CGSize) -> some View {
        if size.width > size.height {
            landscapeCockpit(size: size)
        } else {
            portraitCockpit
        }
    }

    private func landscapeCockpit(size: CGSize) -> some View {
        let railWidth = min(460, max(360, size.width * 0.38))

        return VStack(spacing: 14) {
            HStack(spacing: 14) {
                mapStage
                sideRail
                    .frame(width: railWidth)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            cockpitCommandBar
        }
        .padding(14)
    }

    private var portraitCockpit: some View {
        VStack(spacing: 12) {
            Group {
                switch panelMode {
                case .overview:
                    if route == nil || showPlannerHomeWhileRouteActive {
                        phonePlannerHome
                    } else {
                        phoneActiveRoute
                    }
                case .stops:
                    if stopRailMode == .detail, let stop = selectedStop {
                        phoneStopDetail(stop)
                    } else {
                        phoneStopsList
                    }
                case .settings:
                    phoneRouteIntelligence
                case .voice:
                    phoneVoiceNavigation
                }
            }
            phoneBottomNavigation
        }
        .padding(.horizontal, 14)
        .padding(.top, 12)
        .padding(.bottom, 10)
        .sheet(item: $sharePayload) { payload in
            ShareSheet(activityItems: [payload.text])
        }
    }

    private var phonePlannerHome: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 18) {
                HStack(alignment: .top) {
                    phoneNavTitle(title: "JARVIS", subtitle: "Navigation")
                    Spacer()
                    phoneConceptBadge
                    Button {
                        refreshPlannerHome()
                    } label: {
                        Circle()
                            .fill(
                                RadialGradient(
                                    colors: [slate.opacity(0.95), slate.opacity(0.25), .clear],
                                    center: .center,
                                    startRadius: 2,
                                    endRadius: 20
                                )
                            )
                            .frame(width: 34, height: 34)
                            .overlay(
                                Image(systemName: "location.north.line.fill")
                                    .foregroundStyle(.white)
                            )
                    }
                    .buttonStyle(.plain)
                }

                phoneStoryboardStrip

                VStack(alignment: .leading, spacing: 12) {
                    Text("Where to?")
                        .font(.title3.weight(.semibold))
                        .foregroundStyle(.white)
                    plannerSearchField
                }

                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text("Smart Categories")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white.opacity(0.72))
                        Spacer()
                        Button("See all") {
                            panelMode = .stops
                        }
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(slate)
                    }

                    LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 4), spacing: 10) {
                        ForEach(phoneTiles) { tile in
                            Button {
                                if tile.id != "more" {
                                    selectedStopCategoryID = tile.id
                                }
                                panelMode = .stops
                            } label: {
                                phoneCategoryTile(tile)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }

                phoneRecentPlaces

                routeRecommendationCard

                phoneCapabilityFooter
            }
        }
    }

    private var phoneActiveRoute: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 14) {
                phoneStoryboardStrip

                ZStack(alignment: .topLeading) {
                    mapStage
                        .frame(height: 395)

                    VStack {
                        HStack {
                            if let step = primaryStep {
                                maneuverCard(step)
                                    .frame(maxWidth: 206)
                            }
                            Spacer()
                            VStack(spacing: 10) {
                                mapFloatButton(systemName: "speaker.wave.2.fill")
                                mapFloatButton(systemName: "location.north.fill")
                                mapFloatButton(systemName: "plus")
                            }
                        }
                        Spacer()
                    }
                    .padding(16)
                }

                VStack(spacing: 10) {
                    compactInsightCard(title: "Live Traffic", value: trafficHeadline, detail: trafficDetail, accent: .green)
                    compactInsightCard(title: leaveByHeadline, value: "Arrive \(arrivalTimeText ?? "--")", detail: leaveByDetail, accent: slate)
                }

                HStack(spacing: 12) {
                    circlePhoneAction(systemName: "xmark") {
                        clearRoute()
                    }
                    phoneCenterJarvisAction
                    circlePhoneAction(systemName: "ellipsis") {
                        stopRailMode = .list
                        panelMode = .stops
                    }
                }

                phoneCapabilityFooter
            }
        }
    }

    private var phoneStoryboardStrip: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 10) {
                ForEach(phoneStoryboardStages) { stage in
                    storyboardStep(
                        number: stage.number,
                        title: stage.title,
                        detail: stage.detail,
                        accent: stage.accent
                    )
                }
            }
        }
    }

    private var phoneCapabilityFooter: some View {
        HStack(spacing: 10) {
            capabilityPill(title: "Route Aware", detail: trafficHeadline, tint: slate)
            capabilityPill(title: "Weather Aware", detail: weatherHeadline, tint: .cyan)
            capabilityPill(title: "Family First", detail: familyTravelHeadline, tint: .green)
        }
    }

    private var phoneStopsList: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Button {
                        panelMode = .overview
                    } label: {
                        Image(systemName: "chevron.left")
                            .font(.headline.weight(.bold))
                            .foregroundStyle(.white)
                    }
                    .buttonStyle(.plain)

                    Text("Smart Stops")
                        .font(.title3.weight(.semibold))
                        .foregroundStyle(.white)
                    Spacer()
                    routeFilterChip
                }

                smartCategoryTabs

                if displayedStops.isEmpty {
                    emptyStopsState(title: stopEmptyStateTitle, detail: stopEmptyStateDetail)
                } else {
                    VStack(alignment: .leading, spacing: 18) {
                        if let section = selectedStopSection {
                            phoneSectionHeader(section.label)
                        }

                        ForEach(displayedStops) { stop in
                            Button {
                                selectedStopID = stop.id
                                stopRailMode = .detail
                            } label: {
                                phoneStopRow(stop)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
    }

    private func phoneStopDetail(_ stop: NavigationStop) -> some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Button {
                        stopRailMode = .list
                    } label: {
                        Image(systemName: "chevron.left")
                            .font(.headline.weight(.bold))
                            .foregroundStyle(.white)
                    }
                    .buttonStyle(.plain)
                    Spacer()
                    Button {
                        toggleFavorite(stop.name)
                    } label: {
                        Image(systemName: isFavoriteDestination(stop.name) ? "star.fill" : "star")
                            .foregroundStyle(isFavoriteDestination(stop.name) ? .yellow : .white.opacity(0.88))
                    }
                    .buttonStyle(.plain)
                }

                phoneStopDetailCard(stop)
            }
        }
    }

    private var phoneRouteIntelligence: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Button {
                        panelMode = .overview
                    } label: {
                        Image(systemName: "chevron.left")
                            .font(.headline.weight(.bold))
                            .foregroundStyle(.white)
                    }
                    .buttonStyle(.plain)
                    Text("Route Intelligence")
                        .font(.title3.weight(.semibold))
                        .foregroundStyle(.white)
                    Spacer()
                }

                intelligenceCard(
                    title: "Weather on Route",
                    value: weatherHeadline,
                    detail: weatherDetail,
                    footer: "Light rain starting in 35 min",
                    chartTint: slate
                )

                intelligenceCard(
                    title: "Timing Risk",
                    value: timingRiskHeadline,
                    detail: timingRiskDetail,
                    footer: "No major delays expected",
                    chartTint: stopGreen
                )

                intelligenceCard(
                    title: "Traffic Outlook",
                    value: trafficHeadline,
                    detail: trafficDetail,
                    footer: "Fastest route right now",
                    chartTint: slate
                )

                intelligenceCard(
                    title: "Family & Travel",
                    value: familyTravelHeadline,
                    detail: familyTravelDetail,
                    footer: "Gas prices are average",
                    chartTint: stopGreen
                )
            }
        }
    }

    private var phoneVoiceNavigation: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 16) {
                HStack(alignment: .top) {
                    HStack(spacing: 10) {
                        Circle()
                            .fill(
                                RadialGradient(
                                    colors: [slate.opacity(0.95), slate.opacity(0.24), .clear],
                                    center: .center,
                                    startRadius: 1,
                                    endRadius: 20
                                )
                            )
                            .frame(width: 28, height: 28)
                            .overlay(Image(systemName: "sparkles").foregroundStyle(.white).font(.caption.bold()))
                        VStack(alignment: .leading, spacing: 2) {
                            Text("JARVIS")
                                .font(.title3.weight(.semibold))
                                .foregroundStyle(.white)
                            Text("Voice Navigation")
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.72))
                        }
                    }
                    Spacer()
                    circlePhoneAction(systemName: "xmark") {
                        panelMode = .overview
                    }
                }

                VStack(alignment: .leading, spacing: 12) {
                    phoneVoiceBubble(voicePromptText, outgoing: true)
                    phoneVoiceBubble(voiceResponseText, outgoing: false)
                    if let stop = displayedStops.first ?? selectedStop {
                        HStack(spacing: 12) {
                            ZStack {
                                Circle()
                                    .fill(stopColor(for: stop).opacity(0.2))
                                    .frame(width: 44, height: 44)
                                Image(systemName: stopIcon(for: stop))
                                    .foregroundStyle(stopColor(for: stop))
                            }
                            VStack(alignment: .leading, spacing: 3) {
                                Text(stop.name)
                                    .font(.headline.weight(.semibold))
                                    .foregroundStyle(.white)
                                Text(stop.distanceFromRoute.map { String(format: "%.1f mi off route", $0) } ?? "Along route")
                                    .font(.caption)
                                    .foregroundStyle(.white.opacity(0.62))
                            }
                            Spacer()
                            Text(etaImpactLabel(for: stop))
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(stopGreen)
                        }
                        .padding(14)
                        .background(cardFill, in: RoundedRectangle(cornerRadius: 18))
                    }
                    phoneVoiceBubble(voiceFollowupQuestion, outgoing: true)
                    phoneVoiceBubble(voiceFollowupAnswer, outgoing: false)
                }

                VStack(spacing: 12) {
                    Text(speech.isListening ? "Listening..." : "Tap to ask JARVIS")
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.7))
                    Button {
                        toggleDestinationListening()
                    } label: {
                        ZStack {
                            Circle()
                                .fill(
                                    RadialGradient(
                                        colors: [slate.opacity(0.9), slate.opacity(0.2), .clear],
                                        center: .center,
                                        startRadius: 8,
                                        endRadius: 90
                                    )
                                )
                                .frame(width: 140, height: 140)
                            Circle()
                                .stroke(slate.opacity(0.6), lineWidth: 2)
                                .frame(width: 110, height: 110)
                            Image(systemName: speech.isListening ? "waveform" : "mic.fill")
                                .font(.system(size: 34, weight: .semibold))
                                .foregroundStyle(.white)
                        }
                    }
                    .buttonStyle(.plain)
                }
                .frame(maxWidth: .infinity)
                .padding(.top, 18)
            }
        }
    }

    private var mapStage: some View {
        ZStack(alignment: .topLeading) {
            mapShell
                .clipShape(RoundedRectangle(cornerRadius: 28))
                .overlay(
                    RoundedRectangle(cornerRadius: 28)
                        .stroke(.white.opacity(0.06), lineWidth: 1)
                )

            VStack {
                HStack {
                    if let step = primaryStep {
                        maneuverCard(step)
                    } else {
                        headerCard
                    }
                    Spacer(minLength: 0)
                }
                Spacer()
                HStack(alignment: .bottom) {
                    if let route {
                        routeStatsCard(route)
                    }
                    Spacer(minLength: 0)
                }
            }
            .padding(18)
        }
    }

    private var sideRail: some View {
        VStack(alignment: .leading, spacing: 0) {
            switch panelMode {
            case .overview:
                overviewRailPanel
            case .stops:
                if stopRailMode == .detail, let stop = selectedStop {
                    detailRailPanel(stop)
                } else {
                    stopsRailPanel
                }
            case .settings:
                settingsRailPanel
            case .voice:
                settingsRailPanel
            }
        }
        .frame(maxHeight: .infinity, alignment: .top)
        .background(Color(red: 0.06, green: 0.07, blue: 0.09), in: RoundedRectangle(cornerRadius: 28))
        .overlay(
            RoundedRectangle(cornerRadius: 28)
                .stroke(.white.opacity(0.06), lineWidth: 1)
        )
    }

    private var cockpitCommandBar: some View {
        HStack(spacing: 12) {
            Button {
                clearRoute()
            } label: {
                Label("Exit", systemImage: "arrow.backward")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.plain)
            .commandPillBackground(active: false)

            Button {
                toggleDestinationListening()
            } label: {
                Label(speech.isListening ? "Listening" : "Ask JARVIS", systemImage: speech.isListening ? "waveform" : "sparkles")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.plain)
            .commandPillBackground(active: speech.isListening)

            ForEach(PanelMode.allCases) { mode in
                Button {
                    panelMode = mode
                } label: {
                    Label(mode.title, systemImage: mode.systemImage)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.plain)
                .commandPillBackground(active: panelMode == mode)
            }
        }
        .font(.subheadline.weight(.semibold))
    }

    private func routeStatsCard(_ route: NavigationRouteOverview) -> some View {
        HStack(spacing: 22) {
            routeFooterMetric(title: "arrival", value: arrivalTimeText ?? "--")
            routeFooterMetric(title: "min", value: route.route.durationMinutes.map { "\($0)" } ?? "--")
            routeFooterMetric(title: "mi", value: route.route.distanceMiles.map { String(format: "%.0f", $0) } ?? "--")
            Spacer(minLength: 0)
            Button {
                focusMapOnCurrentContext()
            } label: {
                Image(systemName: "chevron.up")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(.white)
                    .frame(width: 34, height: 34)
                    .background(.white.opacity(0.08), in: Circle())
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 14)
        .frame(maxWidth: 280)
        .background(Color.black.opacity(0.78), in: RoundedRectangle(cornerRadius: 22))
        .overlay(
            RoundedRectangle(cornerRadius: 22)
                .stroke(.white.opacity(0.06), lineWidth: 1)
        )
    }

    private var mapShell: some View {
        ZStack {
            Map(position: $cameraPosition) {
                if let polyline = routePolyline {
                    MapPolyline(polyline)
                        .stroke(slate, lineWidth: 7)
                }

                if let route {
                    Annotation("Origin", coordinate: CLLocationCoordinate2D(latitude: route.origin.lat, longitude: route.origin.lon)) {
                        mapPin(icon: "location.north.circle.fill", color: .white, background: slate)
                    }
                    Annotation("Destination", coordinate: CLLocationCoordinate2D(latitude: route.destination.lat, longitude: route.destination.lon)) {
                        mapPin(icon: "flag.checkered.2.crossed", color: .white, background: stopGreen)
                    }
                } else if let currentCoordinate {
                    Annotation("Current", coordinate: currentCoordinate) {
                        mapPin(icon: "location.fill", color: .white, background: slate)
                    }
                }

                ForEach(mapStops) { stop in
                    if let coordinate = coordinate(for: stop) {
                        Annotation(stop.name, coordinate: coordinate) {
                            mapPin(icon: stopIcon(for: stop), color: .white, background: stopColor(for: stop))
                        }
                    }
                }
            }
            .mapStyle(.standard(elevation: .realistic))
            .overlay {
                LinearGradient(
                    colors: [.black.opacity(0.18), .black.opacity(0.05), .black.opacity(0.35)],
                    startPoint: .top,
                    endPoint: .bottom
                )
                .allowsHitTesting(false)
            }

            VStack {
                Spacer()
                HStack {
                    Spacer()
                    VStack(spacing: 10) {
                        if route != nil {
                            Button {
                                focusMapOnCurrentContext()
                            } label: {
                                Image(systemName: "map")
                                    .font(.system(size: 16, weight: .semibold))
                                    .frame(width: 44, height: 44)
                                    .foregroundStyle(.white)
                                    .background(.black.opacity(0.45), in: Circle())
                            }
                        }

                        Button {
                            centerMapOnUser()
                        } label: {
                            Image(systemName: "location.fill")
                                .font(.system(size: 16, weight: .semibold))
                                .frame(width: 44, height: 44)
                                .foregroundStyle(.white)
                                .background(.black.opacity(0.45), in: Circle())
                        }
                    }
                    .padding(.trailing, 16)
                    .padding(.bottom, 12)
                }
            }
        }
    }

    private var topOverlay: some View {
        VStack(spacing: 12) {
            HStack(alignment: .top, spacing: 10) {
                if let step = primaryStep {
                    maneuverCard(step)
                } else {
                    headerCard
                }
                Spacer(minLength: 0)
            }

            if let route, let stop = selectedStop, panelMode == .stops {
                smartStopsSummary(route: route, stop: stop)
            }
        }
    }

    private var headerCard: some View {
        HStack(spacing: 12) {
            ZStack {
                RoundedRectangle(cornerRadius: 18)
                    .fill(slate.opacity(0.18))
                    .frame(width: 54, height: 54)
                Image(systemName: "sparkles")
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(slate)
            }
            VStack(alignment: .leading, spacing: 4) {
                Text("JARVIS Navigation")
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white)
                Text(route == nil ? "Plan your trip, then let JARVIS rank the best stops along the way." : "Live route intelligence is ready.")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.72))
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
        }
        .padding(14)
        .frame(maxWidth: 360, alignment: .leading)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 24))
        .overlay(
            RoundedRectangle(cornerRadius: 24)
                .stroke(.white.opacity(0.08), lineWidth: 1)
        )
    }

    private func maneuverCard(_ step: NavigationRouteStep) -> some View {
        HStack(spacing: 12) {
            ZStack {
                RoundedRectangle(cornerRadius: 18)
                    .fill(stepAccentColor(for: step).opacity(0.18))
                    .frame(width: 54, height: 54)
                Image(systemName: stepIcon(for: step))
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(stepAccentColor(for: step))
            }
            VStack(alignment: .leading, spacing: 4) {
                Text(step.distanceMiles.map { String(format: "%.0f mi", max(1, $0.rounded())) } ?? "Next")
                    .font(.title2.bold())
                    .foregroundStyle(.white)
                Text(step.instruction.isEmpty ? "Continue on route" : step.instruction)
                    .font(.subheadline)
                    .foregroundStyle(.white.opacity(0.86))
                    .lineLimit(2)
                Text(stepMetaLine(step))
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.64))
                    .lineLimit(1)
            }
            Spacer(minLength: 0)
        }
        .padding(16)
        .frame(maxWidth: 370, alignment: .leading)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 24))
        .overlay(
            RoundedRectangle(cornerRadius: 24)
                .stroke(.white.opacity(0.08), lineWidth: 1)
        )
    }

    private func smartStopsSummary(route: NavigationRouteOverview, stop: NavigationStop) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("Smart Stops Along Route", systemImage: "sparkles")
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white)
                Spacer()
                if loadingStops {
                    ProgressView().tint(.white)
                }
            }

            smartCategoryTabs

            if let section = selectedStopSection {
                stopRow(stop: stop, accent: stopSectionColor(for: section), selected: true)
            }

            Text(stopPanelSummary)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.64))

            Button {
                addStopToCurrentRoute(stop)
            } label: {
                Label("Add Stop to Route", systemImage: "plus.circle")
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.black)
                    .background(stopGreen, in: RoundedRectangle(cornerRadius: 18))
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 28))
        .overlay(
            RoundedRectangle(cornerRadius: 28)
                .stroke(.white.opacity(0.08), lineWidth: 1)
        )
    }

    private var bottomDock: some View {
        VStack(spacing: 12) {
            if let route {
                routeFooter(route)
            }

            panelCard
            commandBar
        }
        .padding(.horizontal, 12)
        .padding(.top, 10)
        .padding(.bottom, 10)
        .background(
            LinearGradient(
                colors: [.clear, .black.opacity(0.22), .black.opacity(0.88)],
                startPoint: .top,
                endPoint: .bottom
            )
        )
    }

    private func routeFooter(_ route: NavigationRouteOverview) -> some View {
        HStack(spacing: 18) {
            routeFooterMetric(title: "Arrival", value: arrivalTimeText ?? "--")
            routeFooterMetric(title: "Drive", value: route.route.durationMinutes.map { "\($0) min" } ?? "--")
            routeFooterMetric(title: "Miles", value: route.route.distanceMiles.map { String(format: "%.0f mi", $0) } ?? "--")
            Spacer()
            Button {
                panelMode = .overview
            } label: {
                Image(systemName: "chevron.up")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(.white)
                    .frame(width: 34, height: 34)
                    .background(.white.opacity(0.08), in: Circle())
            }
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 14)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 24))
        .overlay(
            RoundedRectangle(cornerRadius: 24)
                .stroke(.white.opacity(0.08), lineWidth: 1)
        )
    }

    private func routeFooterMetric(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(value)
                .font(.headline.bold())
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.6))
        }
    }

    private func phoneNavTitle(title: String, subtitle: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.largeTitle.bold())
                .foregroundStyle(.white)
            Text(subtitle)
                .font(.headline)
                .foregroundStyle(slate)
            Text("Concept storyboard with live route continuity.")
                .font(.caption)
                .foregroundStyle(.white.opacity(0.62))
        }
    }

    private var phoneConceptBadge: some View {
        VStack(alignment: .trailing, spacing: 6) {
            HStack(spacing: 8) {
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [slate.opacity(0.9), slate.opacity(0.2), .clear],
                            center: .center,
                            startRadius: 1,
                            endRadius: 18
                        )
                    )
                    .frame(width: 24, height: 24)
                    .overlay(Image(systemName: "location.north.fill").font(.caption2.bold()).foregroundStyle(.white))
                Text("CONCEPT STORYBOARD")
                    .font(.caption2.weight(.semibold))
                    .tracking(1.2)
                    .foregroundStyle(.white.opacity(0.72))
            }
            Text("Route aware. Weather aware.")
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.5))
        }
    }

    private var plannerSearchField: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.white.opacity(0.5))
                TextField("Search destinations", text: $destinationText)
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
                        .foregroundStyle(.white)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 14)
            .background(cardFill, in: RoundedRectangle(cornerRadius: 16))

            if showSuggestions {
                destinationSuggestionsCard
            }
        }
    }

    private var phoneRecentPlaces: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Recent Places")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.72))
                Spacer()
            }

            VStack(spacing: 10) {
                ForEach(Array(savedLocations.prefix(4))) { location in
                    Button {
                        selectedSavedLocationID = location.id
                        queueDestination(location.address, autoPlan: true)
                    } label: {
                        HStack(spacing: 12) {
                            Circle()
                                .fill(slate.opacity(0.22))
                                .frame(width: 34, height: 34)
                                .overlay(Image(systemName: "location.fill").foregroundStyle(slate))

                            VStack(alignment: .leading, spacing: 2) {
                                Text(location.label)
                                    .font(.subheadline.weight(.semibold))
                                    .foregroundStyle(.white)
                                Text(location.address)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                            Spacer()
                            Text(savedLocationDriveEstimate(for: location))
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(stopGreen)
                        }
                        .padding(12)
                        .background(cardFill, in: RoundedRectangle(cornerRadius: 16))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func savedLocationDriveEstimate(for location: NavigationSavedLocation) -> String {
        if location.label.localizedCaseInsensitiveContains("home") { return "12 min" }
        if location.label.localizedCaseInsensitiveContains("work") { return "18 min" }
        return "Trip"
    }

    private func mapFloatButton(systemName: String) -> some View {
        Button {
            if systemName.contains("location") {
                centerMapOnUser()
            } else if systemName == "speaker.wave.2.fill" {
                panelMode = .voice
                if !speech.isListening {
                    toggleDestinationListening()
                }
            } else if systemName == "plus" {
                stopRailMode = .list
                panelMode = .stops
            }
        } label: {
            Image(systemName: systemName)
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(.white)
                .frame(width: 38, height: 38)
                .background(Color.black.opacity(0.48), in: Circle())
        }
        .buttonStyle(.plain)
    }

    private func compactInsightCard(title: String, value: String, detail: String, accent: Color) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.72))
                Spacer()
                Text(value)
                    .font(.caption.weight(.bold))
                    .foregroundStyle(accent)
            }
            Text(detail)
                .font(.subheadline)
                .foregroundStyle(.white)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(cardFill, in: RoundedRectangle(cornerRadius: 18))
    }

    private func circlePhoneAction(systemName: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: systemName)
                .font(.system(size: 17, weight: .bold))
                .foregroundStyle(.white)
                .frame(width: 52, height: 52)
                .background(cardFill, in: Circle())
                .overlay(Circle().stroke(.white.opacity(0.06), lineWidth: 1))
        }
        .buttonStyle(.plain)
    }

    private var phoneCenterJarvisAction: some View {
        Button {
            panelMode = .voice
            if !speech.isListening {
                toggleDestinationListening()
            }
        } label: {
            HStack(spacing: 10) {
                Image(systemName: speech.isListening ? "waveform" : "sparkles")
                    .foregroundStyle(slate)
                    .symbolEffect(.variableColor.iterative, isActive: speech.isListening)
                Text(speech.isListening ? "Listening" : "JARVIS")
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 16)
            .background(cardFill, in: RoundedRectangle(cornerRadius: 24))
            .overlay(
                RoundedRectangle(cornerRadius: 24)
                    .stroke(.white.opacity(0.06), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }

    private func phoneActionPill(title: String, icon: String, active: Bool = false, action: @escaping () -> Void = {}) -> some View {
        Button(action: action) {
            Label(title, systemImage: icon)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .foregroundStyle(active ? .black : .white)
                .background(active ? slate : Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 20))
        }
        .buttonStyle(.plain)
    }

    private func statusChip(_ title: String, tint: Color) -> some View {
        Text(title)
            .font(.caption.weight(.semibold))
            .foregroundStyle(.white)
            .padding(.horizontal, 10)
            .padding(.vertical, 7)
            .background(tint.opacity(0.22), in: Capsule())
    }

    private func phoneSectionHeader(_ title: String) -> some View {
        Text(title.uppercased())
            .font(.caption.weight(.semibold))
            .foregroundStyle(.white.opacity(0.6))
    }

    private func phoneCategoryTile(_ tile: PhoneCategoryTile) -> some View {
        VStack(spacing: 10) {
            ZStack {
                RoundedRectangle(cornerRadius: 14)
                    .fill(tile.color.opacity(0.18))
                    .frame(width: 48, height: 48)
                Image(systemName: tile.icon)
                    .foregroundStyle(tile.color)
            }
            Text(tile.title)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.white)
                .lineLimit(1)
                .minimumScaleFactor(0.75)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .background(cardFill, in: RoundedRectangle(cornerRadius: 18))
        .overlay(
            RoundedRectangle(cornerRadius: 18)
                .stroke(.white.opacity(0.05), lineWidth: 1)
        )
    }

    private func storyboardStep(number: String, title: String, detail: String, accent: Color) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Text(number)
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.white)
                    .frame(width: 24, height: 24)
                    .background(accent.opacity(0.22), in: Circle())
                Text(title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.9))
            }
            Text(detail)
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.6))
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(width: 156, alignment: .leading)
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(cardFill, in: RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(.white.opacity(0.05), lineWidth: 1)
        )
    }

    private func capabilityPill(title: String, detail: String, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption2.weight(.bold))
                .foregroundStyle(tint)
            Text(detail)
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.72))
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(cardFill, in: RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(.white.opacity(0.05), lineWidth: 1)
        )
    }

    private var phoneBottomNavigation: some View {
        HStack {
            phoneBottomItem(title: "Home", icon: "house", active: panelMode == .overview && route == nil) {
                showPlannerHomeWhileRouteActive = true
                panelMode = .overview
            }
            phoneBottomItem(title: "Map", icon: "map", active: panelMode == .overview && route != nil) {
                showPlannerHomeWhileRouteActive = false
                panelMode = .overview
            }
            phoneBottomItem(title: "Trips", icon: "point.bottomleft.forward.to.point.topright.scurvepath", active: panelMode == .settings) {
                panelMode = .settings
            }
            phoneBottomItem(title: "Saved", icon: "bookmark", active: panelMode == .stops) {
                stopRailMode = .list
                panelMode = .stops
            }
            phoneBottomItem(title: "Profile", icon: "person", active: panelMode == .voice) {
                panelMode = .voice
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(cardFill, in: RoundedRectangle(cornerRadius: 20))
        .overlay(
            RoundedRectangle(cornerRadius: 20)
                .stroke(.white.opacity(0.05), lineWidth: 1)
        )
    }

    private func phoneBottomItem(title: String, icon: String, active: Bool = false, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 5) {
                Image(systemName: icon)
                    .font(.system(size: 14, weight: .semibold))
                Text(title)
                    .font(.caption2)
            }
            .frame(maxWidth: .infinity)
            .foregroundStyle(active ? slate : .white.opacity(0.7))
        }
        .buttonStyle(.plain)
    }

    private var routeFilterChip: some View {
        Menu {
            Button("All Smart Stops") {
                if let first = allVisibleSections.first?.id {
                    selectedStopCategoryID = first
                }
            }
            ForEach(allVisibleSections) { section in
                Button(section.label) {
                    selectedStopCategoryID = section.id
                    panelMode = .stops
                }
            }
            if route != nil {
                Divider()
                Button("Route Intelligence") {
                    panelMode = .settings
                }
            }
        } label: {
            HStack(spacing: 7) {
                Image(systemName: "line.3.horizontal.decrease.circle")
                Text(route == nil ? "Planning" : "Along Route")
                Image(systemName: "chevron.down")
                    .font(.caption2.bold())
            }
            .font(.caption.weight(.semibold))
            .foregroundStyle(.white)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(.white.opacity(0.06), in: Capsule())
        }
    }

    private func phoneStopRow(_ stop: NavigationStop) -> some View {
        HStack(spacing: 12) {
            ZStack {
                Circle()
                    .fill(stopColor(for: stop).opacity(0.22))
                    .frame(width: 46, height: 46)
                Image(systemName: stopIcon(for: stop))
                    .foregroundStyle(stopColor(for: stop))
            }

            VStack(alignment: .leading, spacing: 3) {
                Text(stop.name)
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white)
                    .lineLimit(1)
                Text(stop.address)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                Text(stop.distanceFromRoute.map { String(format: "%.1f mi off route", $0) } ?? "Along route")
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.55))
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 3) {
                Text(stop.distanceFromRoute.map { String(format: "%.1f mi", $0) } ?? "--")
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white)
                Text(etaImpactLabel(for: stop))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(stopGreen)
            }
        }
        .padding(12)
        .background(cardFill, in: RoundedRectangle(cornerRadius: 18))
    }

    private func phoneStopDetailCard(_ stop: NavigationStop) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            selectedStopHero(stop)

            VStack(alignment: .center, spacing: 8) {
                Text(stop.name)
                    .font(.title2.weight(.semibold))
                    .foregroundStyle(.white)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity)
                Text(stop.address.isEmpty ? "Open until 9:00 PM" : stop.address)
                    .font(.subheadline)
                    .foregroundStyle(.white.opacity(0.72))
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity)
            }

            HStack(spacing: 8) {
                detailCapsule(icon: "figure.walk", text: stop.distanceFromRoute.map { String(format: "%.1f mi off route", $0) } ?? "Along route", tint: Color.purple)
                detailCapsule(icon: "clock.fill", text: etaImpactLabel(for: stop), tint: stopGreen)
            }

            HStack(spacing: 10) {
                metricStrip(title: stop.rating.map { String(format: "%.1f", $0) } ?? "4.8", subtitle: "reviews")
                metricStrip(title: priceLevelText(for: stop), subtitle: "cost")
            }

            HStack(spacing: 10) {
                miniActionTile(icon: "phone.fill", title: "Call") {
                    callStop(stop)
                }
                miniActionTile(icon: "globe", title: "Website") {
                    openStopWebsite(stop)
                }
                miniActionTile(icon: "square.and.arrow.up", title: "Share") {
                    sharePayload = SharePayload(text: shareText(for: stop))
                }
                miniActionTile(icon: isFavoriteDestination(stop.name) ? "star.fill" : "star", title: "Save") {
                    toggleFavorite(stop.name)
                }
            }

            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("JARVIS Insight")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.68))
                    Spacer()
                    Image(systemName: "waveform")
                        .foregroundStyle(slate)
                }
                Text(stop.description.isEmpty ? "Great stop for a quick coffee. Minimal impact to your ETA." : stop.description)
                    .font(.subheadline)
                    .foregroundStyle(.white)
            }
            .padding(14)
            .background(cardFill, in: RoundedRectangle(cornerRadius: 18))

            VStack(alignment: .leading, spacing: 8) {
                Text("Address")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.68))
                Text(stop.address.isEmpty ? "No street address available" : stop.address)
                    .font(.subheadline)
                    .foregroundStyle(.white)
            }
            .padding(14)
            .background(cardFill, in: RoundedRectangle(cornerRadius: 18))

            Button {
                addStopToCurrentRoute(stop)
            } label: {
                Label("Add to Route", systemImage: "location.fill")
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
            }
            .buttonStyle(.borderedProminent)
            .tint(stopGreen)

            HStack(spacing: 10) {
                Button {
                    openStopInAppleMaps(stop)
                } label: {
                    Label("Open in Apple Maps", systemImage: "map.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(.white)

                Button {
                    openStopInGoogleMaps(stop)
                } label: {
                    Label("Open in Google Maps", systemImage: "globe")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(.white)
            }
        }
    }

    private func detailCapsule(icon: String, text: String, tint: Color) -> some View {
        HStack(spacing: 6) {
            Image(systemName: icon)
            Text(text)
        }
        .font(.caption.weight(.semibold))
        .foregroundStyle(.white)
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(tint.opacity(0.18), in: Capsule())
    }

    private func metricStrip(title: String, subtitle: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.title3.weight(.semibold))
                .foregroundStyle(.white)
            Text(subtitle)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.6))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(cardFill, in: RoundedRectangle(cornerRadius: 16))
    }

    private func miniActionTile(icon: String, title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white)
                Text(title)
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.75))
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(cardFill, in: RoundedRectangle(cornerRadius: 16))
        }
        .buttonStyle(.plain)
    }

    private func intelligenceCard(title: String, value: String, detail: String, footer: String, chartTint: Color) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(title)
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white)
                Spacer()
                Text(value)
                    .font(.headline.weight(.bold))
                    .foregroundStyle(stopGreen)
            }
            Text(detail)
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.82))
            phoneChartBars(tint: chartTint)
            Text(footer)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(16)
        .background(cardFill, in: RoundedRectangle(cornerRadius: 20))
    }

    private func phoneChartBars(tint: Color) -> some View {
        let bars: [CGFloat] = [0.22, 0.34, 0.3, 0.5, 0.46, 0.58, 0.66, 0.48, 0.72, 0.38, 0.52, 0.42]
        return HStack(alignment: .bottom, spacing: 4) {
            ForEach(Array(bars.enumerated()), id: \.offset) { _, height in
                RoundedRectangle(cornerRadius: 3)
                    .fill(tint.opacity(0.92))
                    .frame(maxWidth: .infinity)
                    .frame(height: max(8, 48 * height))
            }
        }
        .frame(height: 52)
        .padding(.top, 4)
    }

    private func phoneVoiceBubble(_ text: String, outgoing: Bool) -> some View {
        HStack {
            if outgoing { Spacer(minLength: 34) }
            Text(text)
                .font(.subheadline)
                .foregroundStyle(.white)
                .padding(.horizontal, 14)
                .padding(.vertical, 12)
                .background((outgoing ? slate.opacity(0.24) : Color.white.opacity(0.055)), in: RoundedRectangle(cornerRadius: 18))
            if !outgoing { Spacer(minLength: 34) }
        }
    }

    private var panelCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            switch panelMode {
            case .overview:
                overviewPanel
            case .stops:
                stopsPanel
            case .settings:
                settingsPanel
            case .voice:
                settingsPanel
            }
        }
        .padding(18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 28))
        .overlay(
            RoundedRectangle(cornerRadius: 28)
                .stroke(.white.opacity(0.08), lineWidth: 1)
        )
    }

    private var overviewPanel: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Label(route == nil ? "Route Planner" : "Trip Overview", systemImage: route == nil ? "location.magnifyingglass" : "map")
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white)
                Spacer()
                if loadingLocations {
                    ProgressView().tint(.white)
                }
            }

            plannerContent

            if let route {
                HStack(spacing: 12) {
                    overviewMetric(icon: "mappin.and.ellipse", title: "Destination", value: route.destination.label)
                    overviewMetric(icon: "exclamationmark.triangle.fill", title: "Alerts", value: alertCountLabel)
                }

                if let sample = leadingRouteSample {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Drive Conditions")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white.opacity(0.68))
                        HStack(spacing: 10) {
                            conditionBadge(label: sample.condition.isEmpty ? "Clear" : sample.condition, icon: routeSampleIcon(for: sample), tint: routeSampleAccent(for: sample))
                            if let temp = sample.temperatureF {
                                conditionBadge(label: "\(Int(temp.rounded()))°", icon: "thermometer.medium", tint: slate)
                            }
                            if let rainPct = sample.rainPct, rainPct > 0 {
                                conditionBadge(label: "\(rainPct)% rain", icon: "cloud.rain.fill", tint: .blue)
                            }
                        }
                    }
                }

                if !upcomingSteps.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Upcoming")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white.opacity(0.68))

                        ForEach(upcomingSteps) { step in
                            HStack(spacing: 10) {
                                Image(systemName: stepIcon(for: step))
                                    .foregroundStyle(stepAccentColor(for: step))
                                    .frame(width: 24)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(step.instruction.isEmpty ? "Continue on route" : step.instruction)
                                        .font(.subheadline.weight(.semibold))
                                        .foregroundStyle(.white)
                                        .lineLimit(2)
                                    Text(stepMetaLine(step))
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                }
            } else {
                quickDestinations
            }
        }
    }

    private var overviewRailPanel: some View {
        ScrollView(showsIndicators: false) {
            overviewPanel
                .padding(22)
        }
    }

    private var plannerContent: some View {
        VStack(alignment: .leading, spacing: 12) {
            Picker("Origin", selection: $selectedOriginMode) {
                ForEach(availableOriginModes) { mode in
                    Text(mode.title).tag(mode)
                }
            }
            .pickerStyle(.segmented)

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
                        .frame(width: 36, height: 36)
                        .foregroundStyle(.white)
                        .background((speech.isListening ? slate : .white.opacity(0.08)), in: Circle())
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 14)
            .background(
                RoundedRectangle(cornerRadius: 18)
                    .fill(.white.opacity(0.06))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 18)
                    .stroke(speech.isListening ? slate.opacity(0.6) : .white.opacity(0.08), lineWidth: 1)
            )

            if speech.isListening || !speech.transcript.isEmpty || speech.errorMessage != nil {
                navigationVoiceStatus
            }

            HStack(spacing: 10) {
                Button {
                    destinationFocused = false
                    Task { await planRoute() }
                } label: {
                    Label(loadingRoute ? "Planning…" : "Plan Route", systemImage: "arrow.triangle.turn.up.right.diamond.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(slate)
                .disabled(loadingRoute || destinationText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

                if let route {
                    Button {
                        openInAppleMaps(route)
                    } label: {
                        Label("Apple Maps", systemImage: "map.fill")
                    }
                    .buttonStyle(.bordered)
                    .tint(.white)
                }
            }

            if showSuggestions {
                destinationSuggestionsCard
            }
        }
    }

    private var quickDestinations: some View {
        VStack(alignment: .leading, spacing: 12) {
            if !favoriteDestinations.isEmpty {
                quickDestinationSection(title: "Favorites", systemImage: "star.fill", items: favoriteDestinations, tint: .yellow)
            }

            if !savedLocations.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 10) {
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
                                .frame(width: 184, alignment: .leading)
                                .background(
                                    RoundedRectangle(cornerRadius: 16)
                                        .fill(location.id == selectedSavedLocationID ? slate.opacity(0.2) : .white.opacity(0.04))
                                )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }

            if !recentDestinations.isEmpty {
                quickDestinationSection(title: "Recent", systemImage: "clock.arrow.circlepath", items: recentDestinations, tint: slate)
            }

            if !routeHistory.isEmpty {
                routeHistorySection
            }
        }
    }

    private func quickDestinationSection(title: String, systemImage: String, items: [String], tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(title, systemImage: systemImage)
                .font(.caption.weight(.semibold))
                .foregroundStyle(tint)
            ForEach(items, id: \.self) { destination in
                Button {
                    queueDestination(destination, autoPlan: true)
                } label: {
                    HStack(spacing: 10) {
                        Image(systemName: systemImage)
                            .foregroundStyle(tint)
                        Text(destination)
                            .font(.subheadline)
                            .foregroundStyle(.white.opacity(0.88))
                            .lineLimit(1)
                        Spacer()
                    }
                }
                .buttonStyle(.plain)
            }
        }
    }

    private var routeHistorySection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Route History", systemImage: "arrow.triangle.swap")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.teal)
            ForEach(Array(routeHistory.prefix(4))) { entry in
                Button {
                    Task { await resumeStoredRoute(entry) }
                } label: {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(entry.destination)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.white)
                            .lineLimit(1)
                        Text("\(entry.origin) -> \(entry.destination)")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                        Text("Previewed \(entry.previewCount)x · Resumed \(entry.resumeCount)x")
                            .font(.caption2)
                            .foregroundStyle(.secondary.opacity(0.85))
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func overviewMetric(icon: String, title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Image(systemName: icon)
                .foregroundStyle(slate)
            Text(value)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.white)
                .lineLimit(2)
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 18)
                .fill(.white.opacity(0.04))
        )
    }

    private func conditionBadge(label: String, icon: String, tint: Color) -> some View {
        HStack(spacing: 6) {
            Image(systemName: icon)
            Text(label)
        }
        .font(.caption.weight(.semibold))
        .foregroundStyle(.white)
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(tint.opacity(0.18), in: Capsule())
    }

    private var stopsPanel: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Smart Stops Along Route")
                        .font(.headline.weight(.semibold))
                        .foregroundStyle(.white)
                    Text(route == nil ? "Plan a drive and JARVIS will rank the best stops for the trip." : stopPanelSummary)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                if loadingStops {
                    ProgressView().tint(.white)
                }
            }

            smartCategoryTabs

            if route == nil {
                emptyStopsState(title: "No active route yet", detail: "Plan a route first, then JARVIS will surface smart stops like Starbucks, food, parks, and historic sites.")
            } else {
                if displayedStops.isEmpty {
                    emptyStopsState(title: stopEmptyStateTitle, detail: stopEmptyStateDetail)
                } else {
                    VStack(alignment: .leading, spacing: 10) {
                        ForEach(displayedStops) { stop in
                            Button {
                                selectedStopID = stop.id
                                stopRailMode = .detail
                            } label: {
                                stopRow(
                                    stop: stop,
                                    accent: stopColor(for: stop),
                                    selected: stop.id == selectedStop?.id
                                )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
    }

    private var stopsRailPanel: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Label("Smart Stops Along Route", systemImage: "sparkles")
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.white)
                Spacer()
                if loadingStops {
                    ProgressView().tint(.white)
                }
            }

            smartCategoryTabs

            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 12) {
                    stopsPanel
                }
            }

            if let stop = selectedStop {
                HStack(spacing: 12) {
                    Button {
                        addStopToCurrentRoute(stop)
                    } label: {
                        Label("Add Stop to Route", systemImage: "plus.circle")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(stopGreen)

                    Button {
                        selectedStopID = stop.id
                        stopRailMode = .detail
                    } label: {
                        Image(systemName: "slider.horizontal.3")
                            .frame(width: 54, height: 50)
                    }
                    .buttonStyle(.bordered)
                    .tint(.white)
                }
            }
        }
        .padding(22)
    }

    private var smartCategoryTabs: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(allVisibleSections) { section in
                    let isSelected = section.id == selectedStopSection?.id
                    Button {
                        selectedStopCategoryID = section.id
                        if activeStopCategoryIDs.contains(section.id) == false {
                            activeStopCategoryIDs.insert(section.id)
                            persistNavigationState(activeStopCategoryIDs: Array(activeStopCategoryIDs))
                        }
                        panelMode = .stops
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: stopSectionIcon(for: section))
                            Text(section.label)
                            Text("\(section.items.count)")
                                .font(.caption2.weight(.bold))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 3)
                                .background((isSelected ? Color.black.opacity(0.12) : stopSectionColor(for: section).opacity(0.2)), in: Capsule())
                        }
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(isSelected ? .black : .white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 10)
                        .background(
                            Capsule()
                                .fill(isSelected ? stopSectionColor(for: section) : .white.opacity(0.06))
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func selectedStopDetail(_ stop: NavigationStop) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            selectedStopHero(stop)

            if !stop.description.isEmpty {
                Text(stop.description)
                    .font(.subheadline)
                    .foregroundStyle(.white.opacity(0.82))
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack(spacing: 10) {
                stopMetricCard(icon: "arrow.triangle.turn.up.right.circle.fill", value: stop.distanceFromRoute.map { String(format: "%.1f mi", $0) } ?? "--", label: "Off route")
                stopMetricCard(icon: "clock.fill", value: etaImpactLabel(for: stop), label: "ETA impact")
                stopMetricCard(icon: "star.fill", value: stop.rating.map { String(format: "%.1f", $0) } ?? "--", label: "Rating")
            }

            HStack(spacing: 10) {
                Button {
                    routeToStop(stop)
                } label: {
                    Label("Start Navigation", systemImage: "location.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(stopGreen)

                Button {
                    addStopToCurrentRoute(stop)
                } label: {
                    Label("Add as Stop", systemImage: "plus.circle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(.white)
            }

            HStack(spacing: 10) {
                Button {
                    openStopInAppleMaps(stop)
                } label: {
                    Label("Apple Maps", systemImage: "map.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(.white)

                Button {
                    openStopInGoogleMaps(stop)
                } label: {
                    Label("Google Maps", systemImage: "globe")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(.white)
            }
        }
    }

    private func detailRailPanel(_ stop: NavigationStop) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Button {
                    stopRailMode = .list
                } label: {
                    Label("Back", systemImage: "chevron.left")
                        .font(.headline.weight(.semibold))
                }
                .buttonStyle(.plain)
                .foregroundStyle(.white)

                Spacer()

                Button {
                    stopRailMode = .list
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundStyle(.white.opacity(0.9))
                        .frame(width: 38, height: 38)
                        .background(.white.opacity(0.06), in: Circle())
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 18)
            .padding(.top, 18)

            ScrollView(showsIndicators: false) {
                selectedStopDetail(stop)
                    .padding(18)
            }
        }
    }

    private func selectedStopHero(_ stop: NavigationStop) -> some View {
        ZStack(alignment: .bottomLeading) {
            if let scene = selectedLookAroundScene {
                LookAroundPreview(initialScene: scene)
                    .frame(height: 220)
                    .clipShape(RoundedRectangle(cornerRadius: 22))
                    .overlay(
                        LinearGradient(
                            colors: [.clear, .black.opacity(0.18), .black.opacity(0.7)],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                        .clipShape(RoundedRectangle(cornerRadius: 22))
                    )
                    .overlay(alignment: .topLeading) {
                        categoryBadge(for: stop)
                            .padding(16)
                    }
            } else {
                RoundedRectangle(cornerRadius: 22)
                    .fill(
                        LinearGradient(
                            colors: [
                                stopColor(for: stop).opacity(0.85),
                                Color(red: 0.12, green: 0.15, blue: 0.2),
                                Color.black
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(height: 220)
                    .overlay(alignment: .topTrailing) {
                        Image(systemName: stopIcon(for: stop))
                            .font(.system(size: 52, weight: .semibold))
                            .foregroundStyle(.white.opacity(0.12))
                            .padding(20)
                    }
                    .overlay(alignment: .topLeading) {
                        categoryBadge(for: stop)
                            .padding(16)
                    }
            }

            VStack(alignment: .leading, spacing: 10) {
                Text(stop.name)
                    .font(.title2.bold())
                    .foregroundStyle(.white)
                    .lineLimit(2)
                if !stop.address.isEmpty {
                    Text(stop.address)
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.86))
                        .lineLimit(2)
                }
            }
            .padding(18)
        }
    }

    private func categoryBadge(for stop: NavigationStop) -> some View {
        HStack(spacing: 6) {
            Image(systemName: stopIcon(for: stop))
            Text(stopCategoryLabel(for: stop))
        }
        .font(.caption.weight(.semibold))
        .foregroundStyle(.white)
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(.black.opacity(0.2), in: Capsule())
    }

    private func stopMetricCard(icon: String, value: String, label: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Image(systemName: icon)
                .foregroundStyle(.white.opacity(0.82))
            Text(value)
                .font(.headline.weight(.semibold))
                .foregroundStyle(.white)
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 18)
                .fill(.white.opacity(0.04))
        )
    }

    private func stopRow(stop: NavigationStop, accent: Color, selected: Bool) -> some View {
        HStack(spacing: 12) {
            ZStack {
                Circle()
                    .fill(accent.opacity(0.18))
                    .frame(width: 48, height: 48)
                Image(systemName: stopIcon(for: stop))
                    .foregroundStyle(accent)
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(stop.name)
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white)
                    .lineLimit(2)
                Text(stop.address)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 4) {
                Text(stop.distanceFromRoute.map { String(format: "%.1f mi", $0) } ?? "--")
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white)
                Text(etaImpactLabel(for: stop))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(stopGreen)
            }
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 20)
                .fill(selected ? .white.opacity(0.08) : .white.opacity(0.04))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 20)
                .stroke(selected ? accent.opacity(0.55) : .white.opacity(0.05), lineWidth: 1)
        )
    }

    private func emptyStopsState(title: String, detail: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline.weight(.semibold))
                .foregroundStyle(.white.opacity(0.9))
            Text(detail)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            if route != nil {
                HStack(spacing: 10) {
                    Button("Reload Stops") {
                        Task { await reloadStopsForActiveRoute() }
                    }
                    .buttonStyle(.bordered)
                    .tint(.white)

                    if selectedStopCategoryID == "parks" || selectedStopCategoryID == "historic" {
                        Button("Widen Search") {
                            parksHistoricRadiusMiles = min(100, parksHistoricRadiusMiles + 10)
                            Task { await reloadStopsForActiveRoute() }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(stopGreen)
                    }
                }
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 18)
                .fill(.white.opacity(0.04))
        )
    }

    private var settingsPanel: some View {
        VStack(alignment: .leading, spacing: 16) {
            Label("Route Controls", systemImage: "slider.horizontal.3")
                .font(.headline.weight(.semibold))
                .foregroundStyle(.white)

            if let route {
                routeIntelOverview(route)
            }

            if allVisibleSections.contains(where: { ["parks", "historic"].contains($0.id) }) {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Parks & Historic Radius")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.white)
                        Spacer()
                        Text("\(Int(parksHistoricRadiusMiles)) mi")
                            .font(.subheadline.weight(.bold))
                            .foregroundStyle(stopGreen)
                    }

                    Slider(
                        value: $parksHistoricRadiusMiles,
                        in: 5...100,
                        step: 5,
                        onEditingChanged: { editing in
                            if !editing {
                                Task { await reloadStopsForActiveRoute() }
                            }
                        }
                    )
                    .tint(stopGreen)
                }
                .padding(14)
                .background(
                    RoundedRectangle(cornerRadius: 18)
                        .fill(.white.opacity(0.04))
                )
            }

            VStack(alignment: .leading, spacing: 10) {
                Text("Stop Categories")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.68))

                ForEach(allVisibleSections) { section in
                    Button {
                        toggleStopCategory(section.id)
                    } label: {
                        HStack {
                            HStack(spacing: 10) {
                                Image(systemName: stopSectionIcon(for: section))
                                    .foregroundStyle(stopSectionColor(for: section))
                                Text(section.label)
                                    .foregroundStyle(.white)
                            }
                            Spacer()
                            Image(systemName: activeStopCategoryIDs.contains(section.id) ? "checkmark.circle.fill" : "circle")
                                .foregroundStyle(activeStopCategoryIDs.contains(section.id) ? stopGreen : .white.opacity(0.3))
                        }
                        .padding(.vertical, 8)
                    }
                    .buttonStyle(.plain)
                }
            }

            if route != nil {
                Button {
                    Task { await refreshRouteIntel() }
                } label: {
                    Label("Refresh Route Intel", systemImage: "arrow.clockwise")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(slate)

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
    }

    private func routeIntelOverview(_ route: NavigationRouteOverview) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Weather + Arrival Intelligence")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.white)

            HStack(spacing: 10) {
                stopMetricCard(icon: leadingRouteSample.map(routeSampleIcon(for:)) ?? "sun.max.fill", value: weatherHeadline, label: weatherDetail)
                stopMetricCard(icon: "clock.badge.checkmark.fill", value: leaveByHeadline, label: leaveByDetail)
                stopMetricCard(icon: "exclamationmark.triangle.fill", value: timingRiskHeadline, label: timingRiskDetail)
            }

            if !weatherSamplePreview.isEmpty {
                VStack(alignment: .leading, spacing: 10) {
                    Text("Route Weather Windows")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.68))
                    ForEach(Array(weatherSamplePreview.enumerated()), id: \.offset) { _, sample in
                        HStack(spacing: 10) {
                            Image(systemName: routeSampleIcon(for: sample))
                                .foregroundStyle(routeSampleAccent(for: sample))
                                .frame(width: 22)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(sample.condition.isEmpty ? "Clear segment" : sample.condition)
                                    .font(.subheadline.weight(.semibold))
                                    .foregroundStyle(.white)
                                Text(routeWeatherLine(for: sample))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                        }
                    }
                }
                .padding(14)
                .background(
                    RoundedRectangle(cornerRadius: 18)
                        .fill(.white.opacity(0.04))
                )
            }

            if !routeAlertLines.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Active Route Alerts")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.orange.opacity(0.95))
                    ForEach(routeAlertLines.prefix(4), id: \.self) { line in
                        HStack(alignment: .top, spacing: 8) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .foregroundStyle(.orange)
                                .padding(.top, 2)
                            Text(line)
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.82))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
                .padding(14)
                .background(
                    RoundedRectangle(cornerRadius: 18)
                        .fill(.orange.opacity(0.08))
                )
            }

            destinationPreviewCard(route)
        }
    }

    private func destinationPreviewCard(_ route: NavigationRouteOverview) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Destination Preview")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.white)
                Spacer()
                Button("Open in Maps") {
                    openInAppleMaps(route)
                }
                .font(.caption.weight(.semibold))
                .buttonStyle(.plain)
                .foregroundStyle(slate)
            }

            ZStack(alignment: .bottomLeading) {
                if let scene = routeLookAroundScene {
                    LookAroundPreview(initialScene: scene)
                        .frame(height: 180)
                        .clipShape(RoundedRectangle(cornerRadius: 20))
                        .overlay(
                            LinearGradient(
                                colors: [.clear, .black.opacity(0.12), .black.opacity(0.6)],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                            .clipShape(RoundedRectangle(cornerRadius: 20))
                        )
                } else {
                    RoundedRectangle(cornerRadius: 20)
                        .fill(
                            LinearGradient(
                                colors: [slate.opacity(0.8), Color(red: 0.1, green: 0.12, blue: 0.16), .black],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(height: 180)
                        .overlay(alignment: .center) {
                            VStack(spacing: 10) {
                                Image(systemName: "binoculars.fill")
                                    .font(.system(size: 28, weight: .semibold))
                                    .foregroundStyle(.white.opacity(0.8))
                                Text("Look Around preview unavailable")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white.opacity(0.82))
                            }
                        }
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text(route.destination.label)
                        .font(.headline.weight(.semibold))
                        .foregroundStyle(.white)
                    Text(arrivalTimeText.map { "ETA \($0)" } ?? "Live destination preview")
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.76))
                }
                .padding(16)
            }
        }
    }

    private var settingsRailPanel: some View {
        ScrollView(showsIndicators: false) {
            settingsPanel
                .padding(22)
        }
    }

    private var commandBar: some View {
        HStack(spacing: 10) {
            Button {
                clearRoute()
            } label: {
                Label("Exit", systemImage: "arrow.backward")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.plain)
            .commandPillBackground(active: false)

            Button {
                toggleDestinationListening()
            } label: {
                Label(speech.isListening ? "Listening" : "Ask JARVIS", systemImage: speech.isListening ? "waveform" : "sparkles")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.plain)
            .commandPillBackground(active: speech.isListening)

            ForEach(PanelMode.allCases) { mode in
                Button {
                    panelMode = mode
                } label: {
                    Label(mode.title, systemImage: mode.systemImage)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.plain)
                .commandPillBackground(active: panelMode == mode)
            }
        }
        .font(.subheadline.weight(.semibold))
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
            RoundedRectangle(cornerRadius: 14)
                .fill(.white.opacity(0.04))
        )
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
            RoundedRectangle(cornerRadius: 16)
                .fill(.white.opacity(0.05))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(.white.opacity(0.08), lineWidth: 1)
        )
    }

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

    private var stopEmptyStateTitle: String {
        loadingStops ? "Refreshing smart stops…" : "No suggested stops surfaced yet for this route."
    }

    private var stopEmptyStateDetail: String {
        if loadingStops {
            return "JARVIS is checking along-the-way coffee, food, parks, historic sites, family stops, and gas."
        }
        if selectedStopCategoryID == "parks" || selectedStopCategoryID == "historic" {
            return "Try widening the parks and historic search radius, or switch to a different route-aware category."
        }
        return "Try another stop category or refresh the route intelligence."
    }

    private var alertCountLabel: String {
        let count = route?.samples.reduce(0) { $0 + $1.alerts.count } ?? 0
        return count == 0 ? "None" : "\(count)"
    }

    private func priceLevelText(for stop: NavigationStop) -> String {
        if stop.name.localizedCaseInsensitiveContains("starbucks") { return "$$" }
        if stop.name.localizedCaseInsensitiveContains("park") { return "Free" }
        if stop.name.localizedCaseInsensitiveContains("historic") { return "$" }
        return "$$"
    }

    private func mapPin(icon: String, color: Color, background: Color) -> some View {
        Image(systemName: icon)
            .font(.system(size: 15, weight: .bold))
            .foregroundStyle(color)
            .padding(9)
            .background(background, in: Circle())
            .overlay(Circle().stroke(.white.opacity(0.16), lineWidth: 1))
    }

    private func coordinate(for stop: NavigationStop) -> CLLocationCoordinate2D? {
        guard let lat = stop.lat, let lng = stop.lng else { return nil }
        return CLLocationCoordinate2D(latitude: lat, longitude: lng)
    }

    private func stopSectionColor(for section: NavigationStopSection) -> Color {
        switch section.id {
        case "food": return .orange
        case "starbucks": return Color(red: 0.0, green: 0.44, blue: 0.29)
        case "parks": return .green
        case "historic": return .purple
        case "family": return .pink
        case "gas": return .yellow
        default: return slate
        }
    }

    private func stopSectionIcon(for section: NavigationStopSection) -> String {
        switch section.id {
        case "food": return "fork.knife"
        case "starbucks": return "cup.and.saucer.fill"
        case "parks": return "tree.fill"
        case "historic": return "building.columns.fill"
        case "family": return "heart.fill"
        case "gas": return "fuelpump.fill"
        default: return "mappin.circle.fill"
        }
    }

    private func stopColor(for stop: NavigationStop) -> Color {
        if let section = allVisibleSections.first(where: { $0.items.contains(where: { $0.id == stop.id }) }) {
            return stopSectionColor(for: section)
        }
        return slate
    }

    private func stopIcon(for stop: NavigationStop) -> String {
        if let section = allVisibleSections.first(where: { $0.items.contains(where: { $0.id == stop.id }) }) {
            return stopSectionIcon(for: section)
        }
        return "mappin.circle.fill"
    }

    private func stopCategoryLabel(for stop: NavigationStop) -> String {
        if let section = allVisibleSections.first(where: { $0.items.contains(where: { $0.id == stop.id }) }) {
            return section.label
        }
        return "Smart Stop"
    }

    private func etaImpactLabel(for stop: NavigationStop) -> String {
        guard let distance = stop.distanceFromRoute else { return "--" }
        let minutes = max(1, Int((distance * 1.8).rounded()))
        return "+\(minutes) min"
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
        if parts.isEmpty {
            return "No weather risk flagged for this segment."
        }
        return parts.joined(separator: " • ")
    }

    private func saveRecentDestination(_ destination: String) {
        let trimmed = destination.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        var next = recentDestinations.filter { $0.caseInsensitiveCompare(trimmed) != .orderedSame }
        next.insert(trimmed, at: 0)
        recentDestinations = Array(next.prefix(5))
        persistNavigationState(recentDestinations: recentDestinations)
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
        persistNavigationState(favoriteDestinations: favoriteDestinations)
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
        showPlannerHomeWhileRouteActive = route == nil
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
                if panelMode == .voice {
                    saveRecentDestination(trimmed)
                }
            }
        }
    }

    private func clearRoute() {
        route = nil
        stopSections = []
        routeError = nil
        currentRouteOriginQuery = ""
        currentRouteDestinationQuery = ""
        pendingRouteRestore = nil
        cameraPosition = .automatic
        panelMode = .overview
        showPlannerHomeWhileRouteActive = true
        selectedStopID = nil
        routeLookAroundScene = nil
        syncStopSelection()
        persistNavigationState(lastRoute: NavigationLastRoute(origin: "", destination: ""))
    }

    private func toggleStopCategory(_ categoryID: String) {
        if activeStopCategoryIDs.contains(categoryID) {
            let remaining = activeStopCategoryIDs.subtracting([categoryID])
            if !remaining.isEmpty {
                activeStopCategoryIDs = remaining
            }
        } else {
            activeStopCategoryIDs.insert(categoryID)
        }
        selectedStopCategoryID = categoryID
        persistNavigationState(activeStopCategoryIDs: Array(activeStopCategoryIDs))
    }

    private func routeToStop(_ stop: NavigationStop) {
        let destination = [stop.name, stop.address]
            .filter { !$0.isEmpty }
            .joined(separator: ", ")
        showPlannerHomeWhileRouteActive = false
        queueDestination(destination, autoPlan: true)
    }

    private func addStopToCurrentRoute(_ stop: NavigationStop) {
        guard let route else {
            routeToStop(stop)
            return
        }

        let waypoint = [stop.name, stop.address]
            .filter { !$0.isEmpty }
            .joined(separator: ", ")
        let source = route.origin.label
        let destination = route.destination.label

        var components = URLComponents(string: "https://maps.apple.com/directions")
        components?.queryItems = [
            URLQueryItem(name: "source", value: source),
            URLQueryItem(name: "destination", value: destination),
            URLQueryItem(name: "waypoint", value: waypoint),
            URLQueryItem(name: "mode", value: "driving")
        ]

        if let url = components?.url {
            UIApplication.shared.open(url)
        } else {
            routeToStop(stop)
        }
    }

    private func openStopInAppleMaps(_ stop: NavigationStop) {
        let query = [stop.name, stop.address]
            .filter { !$0.isEmpty }
            .joined(separator: " ")
            .addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? stop.name
        guard let url = URL(string: "http://maps.apple.com/?q=\(query)") else { return }
        UIApplication.shared.open(url)
    }

    private func openStopInGoogleMaps(_ stop: NavigationStop) {
        let destination = [stop.name, stop.address]
            .filter { !$0.isEmpty }
            .joined(separator: ", ")
            .addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? stop.name

        if let appURL = URL(string: "comgooglemaps://?daddr=\(destination)&directionsmode=driving"),
           UIApplication.shared.canOpenURL(appURL) {
            UIApplication.shared.open(appURL)
            return
        }

        guard let webURL = URL(string: "https://www.google.com/maps/dir/?api=1&destination=\(destination)&travelmode=driving") else { return }
        UIApplication.shared.open(webURL)
    }

    private func callStop(_ stop: NavigationStop) {
        let query = "\(stop.name) phone".addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? stop.name
        if let url = URL(string: "https://www.google.com/search?q=\(query)") {
            UIApplication.shared.open(url)
        }
    }

    private func openStopWebsite(_ stop: NavigationStop) {
        if let url = normalizedStopURL(stop.url) {
            UIApplication.shared.open(url)
            return
        }
        let query = "\(stop.name) \(stop.address) website".addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? stop.name
        if let url = URL(string: "https://www.google.com/search?q=\(query)") {
            UIApplication.shared.open(url)
        }
    }

    private func shareText(for stop: NavigationStop) -> String {
        let parts = [
            stop.name,
            stop.address,
            stop.distanceFromRoute.map { String(format: "%.1f mi off route", $0) },
            "ETA impact \(etaImpactLabel(for: stop))"
        ]
        return parts.compactMap { $0 }.joined(separator: "\n")
    }

    private func normalizedStopURL(_ raw: String) -> URL? {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        if let direct = URL(string: trimmed), direct.scheme != nil {
            return direct
        }
        return URL(string: "https://\(trimmed)")
    }

    private func centerMapOnUser() {
        if let currentCoordinate {
            cameraPosition = .region(
                MKCoordinateRegion(
                    center: currentCoordinate,
                    span: MKCoordinateSpan(latitudeDelta: 0.09, longitudeDelta: 0.09)
                )
            )
        } else if selectedOriginMode == .current {
            loc.requestAndFetch(force: true, userInitiated: true)
        }
    }

    private func refreshPlannerHome() {
        if route != nil {
            focusMapOnCurrentContext()
            return
        }
        Task {
            await loadNavigationLocations()
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

    private func refreshRouteIntel() async {
        guard !currentRouteOriginQuery.isEmpty, !currentRouteDestinationQuery.isEmpty else { return }
        loadingRoute = true
        defer { loadingRoute = false }
        do {
            let overview = try await AppleAPIClient.shared.fetchNavigationRoute(
                origin: currentRouteOriginQuery,
                destination: currentRouteDestinationQuery
            )
            route = overview
            focusMap(on: overview)
            await loadStops(origin: currentRouteOriginQuery, destination: currentRouteDestinationQuery)
            await refreshRouteLookAroundScene()
        } catch {
            routeError = error.localizedDescription
        }
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
            if let state = overview.navigationState {
                hydrateNavigationState(state)
            }
            await restorePendingRouteIfPossible()
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
            currentRouteOriginQuery = origin
            currentRouteDestinationQuery = destination
            panelMode = .stops
            showPlannerHomeWhileRouteActive = false
            focusMap(on: overview)
            await loadStops(origin: origin, destination: destination)
            await refreshRouteLookAroundScene()
            saveRecentDestination(destination)
            persistNavigationState(lastRoute: NavigationLastRoute(origin: origin, destination: destination))
        } catch {
            route = nil
            stopSections = []
            routeError = error.localizedDescription
            routeLookAroundScene = nil
        }
    }

    private func loadStops(origin: String, destination: String) async {
        loadingStops = true
        defer { loadingStops = false }
        do {
            let overview = try await AppleAPIClient.shared.fetchNavigationStops(
                origin: origin,
                destination: destination,
                parksRadiusMiles: Int(parksHistoricRadiusMiles.rounded())
            )
            stopSections = overview.sections
            syncStopSelection()
        } catch {
            stopSections = []
            syncStopSelection()
        }
    }

    private func reloadStopsForActiveRoute() async {
        guard !currentRouteOriginQuery.isEmpty, !currentRouteDestinationQuery.isEmpty else { return }
        await loadStops(origin: currentRouteOriginQuery, destination: currentRouteDestinationQuery)
        persistNavigationState(parksHistoricRadiusMiles: Int(parksHistoricRadiusMiles.rounded()))
    }

    private func syncStopSelection() {
        guard !allVisibleSections.isEmpty else {
            selectedStopID = nil
            selectedLookAroundScene = nil
            return
        }
        if allVisibleSections.contains(where: { $0.id == selectedStopCategoryID }) == false {
            selectedStopCategoryID = allVisibleSections.first?.id ?? selectedStopCategoryID
        }
        if let selectedStopSection,
           selectedStopSection.items.contains(where: { $0.id == selectedStopID }) == false {
            selectedStopID = selectedStopSection.items.first?.id
        } else if selectedStopID == nil {
            selectedStopID = selectedStopSection?.items.first?.id
        }
    }

    private func refreshSelectedStopScene() async {
        guard let stop = selectedStop,
              let coordinate = coordinate(for: stop)
        else {
            await MainActor.run {
                selectedLookAroundScene = nil
            }
            return
        }

        let request = MKLookAroundSceneRequest(coordinate: coordinate)
        request.getSceneWithCompletionHandler { scene, _ in
            Task { @MainActor in
                if selectedStop?.id == stop.id {
                    selectedLookAroundScene = scene
                }
            }
        }
    }

    private func refreshRouteLookAroundScene() async {
        guard let route else {
            await MainActor.run {
                routeLookAroundScene = nil
            }
            return
        }

        let coordinate = CLLocationCoordinate2D(latitude: route.destination.lat, longitude: route.destination.lon)
        let request = MKLookAroundSceneRequest(coordinate: coordinate)
        request.getSceneWithCompletionHandler { scene, _ in
            Task { @MainActor in
                if self.route?.destination.label == route.destination.label {
                    routeLookAroundScene = scene
                }
            }
        }
    }

    private func hydrateNavigationState(_ state: NavigationState) {
        favoriteDestinations = state.favoriteDestinations
        recentDestinations = state.recentDestinations
        routeHistory = state.routeHistory
        activeStopCategoryIDs = Set(state.activeStopCategoryIDs.isEmpty ? ["food", "starbucks", "parks", "historic", "family"] : state.activeStopCategoryIDs)
        parksHistoricRadiusMiles = Double(state.parksHistoricRadiusMiles)
        selectedStopCategoryID = state.activeStopCategoryIDs.first ?? selectedStopCategoryID
        if let restoredOriginMode = OriginMode(rawValue: state.selectedOriginMode),
           availableOriginModes.contains(restoredOriginMode) {
            selectedOriginMode = restoredOriginMode
        }
        if !state.selectedSavedLocationID.isEmpty {
            selectedSavedLocationID = state.selectedSavedLocationID
        }
        if destinationText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
           !state.lastRoute.destination.isEmpty {
            destinationText = state.lastRoute.destination
        }
        if !state.lastRoute.origin.isEmpty, !state.lastRoute.destination.isEmpty {
            pendingRouteRestore = state.lastRoute
        }
    }

    private func persistNavigationState(
        favoriteDestinations: [String]? = nil,
        recentDestinations: [String]? = nil,
        activeStopCategoryIDs: [String]? = nil,
        parksHistoricRadiusMiles: Int? = nil,
        selectedOriginMode: String? = nil,
        selectedSavedLocationID: String? = nil,
        lastRoute: NavigationLastRoute? = nil
    ) {
        let patch = NavigationStatePatch(
            favoriteDestinations: favoriteDestinations,
            recentDestinations: recentDestinations,
            activeStopCategoryIDs: activeStopCategoryIDs,
            parksHistoricRadiusMiles: parksHistoricRadiusMiles,
            selectedOriginMode: selectedOriginMode,
            selectedSavedLocationID: selectedSavedLocationID,
            lastRoute: lastRoute
        )
        Task {
            _ = try? await AppleAPIClient.shared.updateNavigationState(patch)
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

    private func restorePendingRouteIfPossible() async {
        guard route == nil,
              !loadingRoute,
              !restoringRoute,
              let pendingRouteRestore,
              !pendingRouteRestore.destination.isEmpty
        else { return }

        if selectedOriginMode == .current, currentCoordinate == nil {
            return
        }

        restoringRoute = true
        defer { restoringRoute = false }

        do {
            let origin = try await resolveOriginQuery()
            let destination = pendingRouteRestore.destination
            let overview = try await AppleAPIClient.shared.fetchNavigationRoute(origin: origin, destination: destination)
            route = overview
            currentRouteOriginQuery = origin
            currentRouteDestinationQuery = destination
            destinationText = destination
            panelMode = .stops
            showPlannerHomeWhileRouteActive = false
            focusMap(on: overview)
            await loadStops(origin: origin, destination: destination)
            self.pendingRouteRestore = nil
        } catch {
            routeError = error.localizedDescription
        }
    }

    private func resumeStoredRoute(_ entry: NavigationRouteHistoryEntry) async {
        loadingRoute = true
        routeError = nil
        defer { loadingRoute = false }

        do {
            let state = try await AppleAPIClient.shared.resumeNavigationHistoryRoute(entry.routeID)
            routeHistory = state.routeHistory
            recentDestinations = state.recentDestinations
            favoriteDestinations = state.favoriteDestinations
            if let restoredOriginMode = OriginMode(rawValue: state.selectedOriginMode),
               availableOriginModes.contains(restoredOriginMode) {
                selectedOriginMode = restoredOriginMode
            }
            selectedSavedLocationID = state.selectedSavedLocationID.isEmpty ? selectedSavedLocationID : state.selectedSavedLocationID
            pendingRouteRestore = state.lastRoute
            destinationText = state.lastRoute.destination
            await restorePendingRouteIfPossible()
        } catch {
            routeError = error.localizedDescription
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

private struct ShareSheet: UIViewControllerRepresentable {
    let activityItems: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}

private extension View {
    func commandPillBackground(active: Bool) -> some View {
        self
            .foregroundStyle(active ? .white : .white.opacity(0.78))
            .padding(.horizontal, 12)
            .padding(.vertical, 14)
            .background(
                RoundedRectangle(cornerRadius: 18)
                    .fill(active ? Color(red: 0.09, green: 0.11, blue: 0.15) : .white.opacity(0.04))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 18)
                    .stroke(active ? Color(red: 0.18, green: 0.62, blue: 0.95).opacity(0.55) : .white.opacity(0.06), lineWidth: 1)
            )
    }
}

#Preview {
    NavigateView()
}
