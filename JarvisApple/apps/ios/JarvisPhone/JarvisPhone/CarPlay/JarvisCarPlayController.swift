import CarPlay
import JarvisKit
import MapKit

@MainActor
final class JarvisCarPlayController: NSObject, @preconcurrency CPListTemplateDelegate, CPMapTemplateDelegate {
    private struct NavigationTripBundle {
        let trip: CPTrip
        let routeChoice: CPRouteChoice
        let tripEstimates: CPTravelEstimates
        let maneuvers: [CPManeuver]
        let routeKey: String
    }

    private enum RouteSectionHeader {
        static let activeRoute = "Active Route"
        static let nextTurns = "Next Turns"
        static let guidance = "Guidance"
        static let destinations = "Go Again"
        static let smartStops = "Smart Stops"
        static let tripSetup = "Trip Setup"
    }

    private enum ConversationSectionHeader {
        static let status = "Conversation Ready"
        static let prompts = "Try Asking"
        static let context = "Recent Context"
        static let followUp = "Try Next"
    }

    private enum IntelligenceSectionHeader {
        static let driveContext = "Drive Context"
        static let whatMatters = "What Matters"
        static let needsYou = "Needs You"
        static let inMotion = "Already Moving"
        static let backend = "Backend Pulse"
    }

    private enum IntelligenceAction {
        case need(NeedsItem)
        case publishReview(PublishReview)
    }

    private let interfaceController: CPInterfaceController
    private let client = AppleAPIClient.shared
    private var refreshTimer: Timer?

    private let briefTemplate = CPListTemplate(title: "JARVIS Brief", sections: [])
    private let needsTemplate = CPListTemplate(title: "Needs You", sections: [])
    private let publishTemplate = CPListTemplate(title: "Publish", sections: [])
    private let opsTemplate = CPListTemplate(title: "Catalyst", sections: [])
    private let mapTemplate = CPMapTemplate()
    private let routeTemplate = CPListTemplate(title: "Routes", sections: [])
    private let conversationTemplate = CPListTemplate(title: "Talk", sections: [])
    private let intelligenceTemplate = CPListTemplate(title: "Intel", sections: [])

    private var latestBriefing: BriefingPacket?
    private var voiceState: VoiceConsoleState?
    private var activeConversationId = ""
    private var conversationPrompts: [String] = []
    private var activeConversationFollowUps: [String] = []
    private var activeConversationTemplate: CPListTemplate?
    private var pendingNeeds: [NeedsItem] = []
    private var navigationChoices: [CarPlayNavigationChoice] = []
    private var navigationOverview: NavigationLocationsOverview?
    private var currentRoute: NavigationRouteOverview?
    private var activeRouteStops: [NavigationStop] = []
    private var activeRouteTemplate: CPListTemplate?
    private var routeCurrentItemSelectable = false
    private var activeTrip: CPTrip?
    private var activeRouteChoice: CPRouteChoice?
    private var activeRouteKey: String?
    private var navigationSession: CPNavigationSession?
    private var publishQueue: [CarPlayPublishQueueEntry] = []
    private var publishReviews: [PublishReview] = []
    private var publishLaunchWorkspace: PublishLaunchWorkspace?
    private var publishHistory: [PublishHistoryEntry] = []
    private var opsOverview: CarPlayOpsOverview?
    private var intelligenceActions: [IntelligenceAction] = []

    init(interfaceController: CPInterfaceController) {
        self.interfaceController = interfaceController
        super.init()
    }

    func start() {
        mapTemplate.mapDelegate = self
        mapTemplate.guidanceBackgroundColor = UIColor(red: 0.06, green: 0.16, blue: 0.28, alpha: 1.0)
        mapTemplate.tripEstimateStyle = .dark
        mapTemplate.automaticallyHidesNavigationBar = false
        mapTemplate.hidesButtonsWithNavigationBar = false

        routeTemplate.delegate = self
        conversationTemplate.delegate = self
        intelligenceTemplate.delegate = self
        updateNavigationControls()

        interfaceController.setRootTemplate(mapTemplate, animated: false, completion: nil)

        Task { await refreshAll() }
        refreshTimer = Timer.scheduledTimer(withTimeInterval: 90, repeats: true) { [weak self] _ in
            guard let self else { return }
            Task { await self.refreshAll() }
        }
    }

    func stop() {
        refreshTimer?.invalidate()
        refreshTimer = nil
        navigationSession?.cancelTrip()
        navigationSession = nil
    }

    private func refreshAll() async {
        async let route = loadNavigation()
        async let conversation = loadConversation()
        async let intelligence = loadIntelligence()
        _ = await (route, conversation, intelligence)
    }

    private func buildBriefSections(from packet: BriefingPacket) -> [CPListSection] {
        var sections: [CPListSection] = []

        let greetItem = CPListItem(text: packet.greeting, detailText: packet.mode.capitalized + " mode")
        greetItem.setImage(UIImage(systemName: "brain.head.profile"))
        sections.append(CPListSection(items: [greetItem], header: nil, sectionIndexTitle: nil))

        if !packet.briefingItems.isEmpty {
            let items: [CPListItem] = packet.briefingItems.prefix(6).map { item in
                let listItem = CPListItem(text: item.text, detailText: item.agent)
                if item.priority == "high" {
                    listItem.setImage(
                        UIImage(systemName: "exclamationmark.circle.fill")?
                            .withTintColor(.systemOrange, renderingMode: .alwaysOriginal)
                    )
                }
                return listItem
            }
            sections.append(CPListSection(items: items, header: "Intelligence", sectionIndexTitle: nil))
        }

        if !packet.workingItems.isEmpty {
            let items: [CPListItem] = packet.workingItems.prefix(3).map { item in
                CPListItem(text: item.agent, detailText: item.action)
            }
            sections.append(CPListSection(items: items, header: "Agents Working", sectionIndexTitle: nil))
        }

        return sections
    }

    private func loadConversation() async {
        do {
            let state = try await client.fetchVoiceState(conversationId: activeConversationId)
            voiceState = state
            if !state.conversation.conversationId.isEmpty {
                activeConversationId = state.conversation.conversationId
            }

            let statusDetail = [
                state.voiceStack.providerLabel,
                state.voiceStack.voiceLabel,
                state.voiceStack.detail,
            ]
                .filter { !$0.isEmpty }
                .joined(separator: " · ")
            let statusItem = CPListItem(
                text: state.voiceStack.cloudReady || state.voiceStack.localReady ? "Voice ready" : "Voice limited",
                detailText: statusDetail.isEmpty ? "Conversation lane is available." : statusDetail
            )
            statusItem.setImage(
                UIImage(systemName: state.voiceStack.cloudReady || state.voiceStack.localReady ? "waveform.circle.fill" : "exclamationmark.waveform")?
                    .withTintColor(state.voiceStack.cloudReady || state.voiceStack.localReady ? .systemBlue : .systemOrange, renderingMode: .alwaysOriginal)
            )

            let threadDetail = state.conversation.latestAssistantText.isEmpty
                ? state.conversation.title
                : state.conversation.latestAssistantText
            let threadItem = CPListItem(
                text: state.conversation.turnCount > 0 ? "Current thread" : "Start a route-aware thread",
                detailText: threadDetail.isEmpty ? "JARVIS is ready for a hands-free route question." : threadDetail
            )
            threadItem.setImage(
                UIImage(systemName: "bubble.left.and.bubble.right.fill")?
                    .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
            )

            conversationPrompts = mergedConversationPrompts(
                primary: state.quickCommands,
                fallback: fallbackConversationPrompts()
            )
            let promptItems = conversationPrompts.map { prompt in
                let item = CPListItem(text: prompt, detailText: "Send this to JARVIS")
                item.setImage(
                    UIImage(systemName: "mic.fill")?
                        .withTintColor(.systemPurple, renderingMode: .alwaysOriginal)
                )
                return item
            }

            let recentTurns = state.conversation.recentTurns.suffix(2)
            let contextItems: [CPListItem]
            if recentTurns.isEmpty {
                let item = CPListItem(text: "No recent exchange yet", detailText: "Use a suggested prompt to start a driving-safe thread.")
                item.setImage(
                    UIImage(systemName: "clock.badge.questionmark")?
                        .withTintColor(.systemGray, renderingMode: .alwaysOriginal)
                )
                contextItems = [item]
            } else {
                contextItems = recentTurns.map { turn in
                    let label = turn.role.lowercased() == "assistant" ? "JARVIS" : "You"
                    let item = CPListItem(text: label, detailText: turn.text)
                    item.setImage(
                        UIImage(systemName: turn.role.lowercased() == "assistant" ? "brain.head.profile" : "person.fill")?
                            .withTintColor(turn.role.lowercased() == "assistant" ? .systemBlue : .systemGray, renderingMode: .alwaysOriginal)
                    )
                    return item
                }
            }

            conversationTemplate.updateSections([
                CPListSection(items: [statusItem, threadItem], header: ConversationSectionHeader.status, sectionIndexTitle: nil),
                CPListSection(items: promptItems, header: ConversationSectionHeader.prompts, sectionIndexTitle: nil),
                CPListSection(items: contextItems, header: ConversationSectionHeader.context, sectionIndexTitle: nil),
            ])
        } catch {
            conversationPrompts = fallbackConversationPrompts()
            let item = CPListItem(text: "Couldn't load conversation", detailText: error.localizedDescription)
            conversationTemplate.updateSections([CPListSection(items: [item])])
        }
    }

    private func loadIntelligence() async {
        async let briefingTask: BriefingPacket? = try? await client.fetchBriefing()
        async let needsTask: [NeedsItem]? = try? await client.fetchNeeds()
        async let publishTask: PublishOverview? = try? await client.fetchPublishing()
        async let opsTask: CarPlayOpsOverview? = try? await client.fetchCarPlayOps()

        latestBriefing = await briefingTask
        pendingNeeds = await needsTask ?? []
        let publish = await publishTask
        publishReviews = publish?.pendingReviews ?? []
        opsOverview = await opsTask

        intelligenceActions = []
        var sections: [CPListSection] = []

        var driveContextItems: [CPListItem] = []
        if let headline = currentRoute.flatMap({ JarvisCarPlayPresentation.currentRouteHeadline(state: navigationOverview?.navigationState, route: $0) }) ??
            JarvisCarPlayPresentation.currentRouteHeadline(state: navigationOverview?.navigationState, route: nil) {
            let item = CPListItem(text: headline.title, detailText: headline.detail)
            item.setImage(
                UIImage(systemName: "arrow.triangle.turn.up.right.circle.fill")?
                    .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
            )
            driveContextItems.append(item)
        }
        if let focus = opsOverview?.currentFocus {
            let item = CPListItem(
                text: "Shared focus: \(focus.module)",
                detailText: focus.reason.isEmpty ? "JARVIS is keeping that lane warm in the background." : focus.reason
            )
            item.setImage(
                UIImage(systemName: "scope")?
                    .withTintColor(.systemOrange, renderingMode: .alwaysOriginal)
            )
            driveContextItems.append(item)
        }
        if driveContextItems.isEmpty {
            let item = CPListItem(text: "No active drive context yet", detailText: "Trip context will sharpen once a route or timing pressure is active.")
            driveContextItems = [item]
        }
        sections.append(CPListSection(items: driveContextItems, header: IntelligenceSectionHeader.driveContext, sectionIndexTitle: nil))

        if let briefing = latestBriefing {
            let briefItems = briefing.briefingItems.prefix(3).map { entry in
                let item = CPListItem(text: entry.text, detailText: entry.agent)
                if entry.priority == "high" {
                    item.setImage(
                        UIImage(systemName: "exclamationmark.circle.fill")?
                            .withTintColor(.systemOrange, renderingMode: .alwaysOriginal)
                    )
                }
                return item
            }
            if !briefItems.isEmpty {
                sections.append(CPListSection(items: Array(briefItems), header: IntelligenceSectionHeader.whatMatters, sectionIndexTitle: nil))
            }
        }

        var needsItems: [CPListItem] = []
        for need in pendingNeeds.prefix(2) {
            intelligenceActions.append(.need(need))
            needsItems.append(
                CPListItem(text: need.text, detailText: "\(need.agent) · \(need.risk.capitalized) risk", image: riskImage(for: need.risk), showsDisclosureIndicator: false)
            )
        }
        for review in publishReviews.prefix(2) {
            intelligenceActions.append(.publishReview(review))
            let item = CPListItem(
                text: review.title,
                detailText: review.stageDisplay.isEmpty ? review.stageKey : review.stageDisplay,
                image: UIImage(systemName: "doc.text.magnifyingglass")?
                    .withTintColor(.systemOrange, renderingMode: .alwaysOriginal),
                showsDisclosureIndicator: false
            )
            needsItems.append(item)
        }
        if needsItems.isEmpty {
            let item = CPListItem(text: "No approvals waiting", detailText: "Nothing in JARVIS is asking for a decision right now.")
            item.setImage(
                UIImage(systemName: "checkmark.circle.fill")?
                    .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
            )
            needsItems = [item]
        }
        sections.append(CPListSection(items: needsItems, header: IntelligenceSectionHeader.needsYou, sectionIndexTitle: nil))

        var inMotionItems: [CPListItem] = []
        if let briefing = latestBriefing {
            inMotionItems.append(contentsOf: briefing.workingItems.prefix(2).map { item in
                let row = CPListItem(text: item.agent, detailText: item.action)
                row.setImage(
                    UIImage(systemName: "gearshape.2.fill")?
                        .withTintColor(.systemTeal, renderingMode: .alwaysOriginal)
                )
                return row
            })
        }
        if let launch = publish?.launchControl {
            let detail = [launch.phase.replacingOccurrences(of: "_", with: " ").capitalized, launch.nextAction]
                .filter { !$0.isEmpty }
                .joined(separator: " · ")
            let item = CPListItem(text: launch.title, detailText: detail)
            item.setImage(
                UIImage(systemName: "shippingbox.fill")?
                    .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
            )
            inMotionItems.append(item)
        }
        if let firstAgent = opsOverview?.agentOps.first {
            let detail = [firstAgent.assignment, firstAgent.attentionReason.isEmpty ? firstAgent.purpose : firstAgent.attentionReason]
                .filter { !$0.isEmpty }
                .joined(separator: " · ")
            let item = CPListItem(text: "\(firstAgent.name) · \(firstAgent.status.capitalized)", detailText: detail)
            item.setImage(
                UIImage(systemName: "person.2.badge.gearshape.fill")?
                    .withTintColor(.systemPurple, renderingMode: .alwaysOriginal)
            )
            inMotionItems.append(item)
        }
        if inMotionItems.isEmpty {
            let item = CPListItem(text: "No active backend motion yet", detailText: "JARVIS will surface background work here once it is live.")
            inMotionItems = [item]
        }
        sections.append(CPListSection(items: inMotionItems, header: IntelligenceSectionHeader.inMotion, sectionIndexTitle: nil))

        var backendItems: [CPListItem] = []
        if let mission = opsOverview?.missionSummary, !mission.headline.isEmpty {
            let item = CPListItem(text: "Mission pressure", detailText: mission.headline)
            item.setImage(
                UIImage(systemName: "flag.2.crossed.fill")?
                    .withTintColor(.systemRed, renderingMode: .alwaysOriginal)
            )
            backendItems.append(item)
        }
        if let activity = opsOverview?.recentActivity.first {
            let item = CPListItem(
                text: activity.title,
                detailText: [activity.detail, activity.routeLabel].filter { !$0.isEmpty }.joined(separator: " · ")
            )
            item.setImage(
                UIImage(systemName: "clock.arrow.circlepath")?
                    .withTintColor(.systemGray, renderingMode: .alwaysOriginal)
            )
            backendItems.append(item)
        }
        if let memory = voiceState?.memoryOverview {
            let detail = [
                "\(memory.profileFactCount) profile facts",
                "\(memory.pendingProposals) pending memory proposals",
                memory.longHorizonLines.first ?? "",
            ]
                .filter { !$0.isEmpty }
                .joined(separator: " · ")
            let item = CPListItem(text: "Continuity memory", detailText: detail)
            item.setImage(
                UIImage(systemName: "brain")?
                    .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
            )
            backendItems.append(item)
        }
        if backendItems.isEmpty {
            let item = CPListItem(text: "Backend pulse is quiet", detailText: "All-of-JARVIS context will surface here when it meaningfully changes the drive.")
            backendItems = [item]
        }
        sections.append(CPListSection(items: backendItems, header: IntelligenceSectionHeader.backend, sectionIndexTitle: nil))

        intelligenceTemplate.updateSections(sections)
    }

    private func loadNeeds() async {
        do {
            let needs = try await client.fetchNeeds()
            pendingNeeds = needs

            if needs.isEmpty {
                let item = CPListItem(text: "All clear", detailText: "No approvals waiting")
                item.setImage(
                    UIImage(systemName: "checkmark.circle.fill")?
                        .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
                )
                needsTemplate.updateSections([CPListSection(items: [item])])
                return
            }

            let items: [CPListItem] = needs.map { need in
                CPListItem(
                    text: need.text,
                    detailText: need.agent,
                    image: riskImage(for: need.risk),
                    showsDisclosureIndicator: false
                )
            }

            needsTemplate.updateSections([
                CPListSection(items: items, header: "\(needs.count) pending", sectionIndexTitle: nil),
            ])
        } catch {
            let item = CPListItem(text: "Couldn't load", detailText: error.localizedDescription)
            needsTemplate.updateSections([CPListSection(items: [item])])
        }
    }

    private func loadNavigation() async {
        do {
            let overview = try await client.fetchNavigationLocations()
            navigationOverview = overview
            navigationChoices = JarvisCarPlayPresentation.navigationChoices(from: overview)
            activeRouteStops = []

            var routeHeadline: (title: String, detail: String)?
            if let lastRoute = overview.navigationState?.lastRoute,
               !lastRoute.origin.isEmpty,
               !lastRoute.destination.isEmpty {
                do {
                    let liveRoute = try await client.fetchNavigationRoute(
                        origin: lastRoute.origin,
                        destination: lastRoute.destination
                    )
                    currentRoute = liveRoute
                    if let stops = try? await client.fetchNavigationStops(
                        origin: lastRoute.origin,
                        destination: lastRoute.destination
                    ) {
                        activeRouteStops = Array(stops.sections.flatMap(\.items).prefix(4))
                    }
                    routeHeadline = JarvisCarPlayPresentation.currentRouteHeadline(
                        state: overview.navigationState,
                        route: liveRoute
                    )
                } catch {
                    currentRoute = nil
                    routeHeadline = JarvisCarPlayPresentation.currentRouteHeadline(
                        state: overview.navigationState,
                        route: nil
                    )
                }
            } else {
                currentRoute = nil
            }

            var sections: [CPListSection] = []
            let overviewItem = CPListItem(
                text: routeHeadline?.title ?? "Navigation is ready",
                detailText: routeHeadline?.detail.isEmpty == false
                    ? routeHeadline?.detail
                    : "Choose a destination from the phone or saved places to start navigation."
            )
            overviewItem.setImage(
                UIImage(systemName: "arrow.turn.up.right")?
                    .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
            )
            let conditionItem = CPListItem(
                text: "Road Conditions",
                detailText: currentRoute?.hazardActive == true
                    ? "Hazard active. Use voice guidance before leaving."
                    : "No major route hazard surfaced in the live preview."
            )
            conditionItem.setImage(
                UIImage(systemName: "cloud.sun.rain.fill")?
                    .withTintColor(.systemTeal, renderingMode: .alwaysOriginal)
            )
            sections.append(CPListSection(items: [overviewItem, conditionItem], header: RouteSectionHeader.activeRoute, sectionIndexTitle: nil))

            routeCurrentItemSelectable = currentRoute != nil
            if let route = currentRoute {
                let currentItem = CPListItem(
                    text: route.route.steps.first?.instruction.isEmpty == false ? route.route.steps.first?.instruction ?? "Open active route" : "Open active route",
                    detailText: JarvisCarPlayPresentation.routeDetail(for: route)
                )
                currentItem.setImage(
                    UIImage(systemName: "location.fill")?
                        .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
                )
                let stepItems = route.route.steps.dropFirst().prefix(3).map { step in
                    let detail = [
                        step.name,
                        step.distanceMiles.map { String(format: "%.1f mi", $0) } ?? "",
                    ]
                        .filter { !$0.isEmpty }
                        .joined(separator: " · ")
                    let item = CPListItem(text: step.instruction, detailText: detail)
                    item.setImage(UIImage(systemName: "arrow.turn.up.right"))
                    return item
                }
                sections.append(CPListSection(items: [currentItem] + stepItems, header: RouteSectionHeader.nextTurns, sectionIndexTitle: nil))
            }

            let voiceItem = CPListItem(
                text: "Voice Guidance",
                detailText: currentRoute?.hazardActive == true
                    ? "Ask JARVIS about weather, delays, and leave-by timing."
                    : "Hands-free guidance is ready for the next route question."
            )
            voiceItem.setImage(
                UIImage(systemName: "waveform")?
                    .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
            )
            let liveViewItem = CPListItem(
                text: "Drive Focus",
                detailText: currentRoute == nil
                    ? "A focused route surface appears once a trip is active."
                    : "Focused in-car guidance keeps the next move front and center."
            )
            liveViewItem.setImage(
                UIImage(systemName: "viewfinder.circle")?
                    .withTintColor(.systemPurple, renderingMode: .alwaysOriginal)
            )
            sections.append(CPListSection(items: [voiceItem, liveViewItem], header: RouteSectionHeader.guidance, sectionIndexTitle: nil))

            if navigationChoices.isEmpty {
                let item = CPListItem(text: "No destinations yet", detailText: "Save family places or recent trips from the phone app.")
                sections.append(CPListSection(items: [item], header: RouteSectionHeader.destinations, sectionIndexTitle: nil))
            } else {
                let items = navigationChoices.map { choice in
                    let item = CPListItem(text: choice.title, detailText: choice.detail)
                    item.setImage(icon(for: choice.source))
                    return item
                }
                sections.append(CPListSection(items: items, header: RouteSectionHeader.destinations, sectionIndexTitle: nil))
            }

            if activeRouteStops.isEmpty {
                let item = CPListItem(text: "No smart stops surfaced", detailText: "Fuel, coffee, and food will appear once a route is active.")
                sections.append(CPListSection(items: [item], header: RouteSectionHeader.smartStops, sectionIndexTitle: nil))
            } else {
                let items = activeRouteStops.map { stop in
                    let detail = [
                        stop.address,
                        stop.distanceFromRoute.map { String(format: "+%.1f mi", $0) } ?? "",
                    ]
                        .filter { !$0.isEmpty }
                        .joined(separator: " · ")
                    let item = CPListItem(text: stop.name, detailText: detail)
                    item.setImage(
                        UIImage(systemName: "mappin.and.ellipse")?
                            .withTintColor(.systemOrange, renderingMode: .alwaysOriginal)
                    )
                    return item
                }
                sections.append(CPListSection(items: items, header: RouteSectionHeader.smartStops, sectionIndexTitle: nil))
            }

            let originItem = CPListItem(
                text: "Origin",
                detailText: JarvisCarPlayPresentation.preferredOriginLabel(from: overview)
            )
            let plannerItem = CPListItem(
                text: "Planner Mode",
                detailText: overview.navigationState?.selectedOriginMode == "current"
                    ? "Using live location as the route origin."
                    : "Using your preferred saved origin."
            )
            plannerItem.setImage(
                UIImage(systemName: "slider.horizontal.3")?
                    .withTintColor(.systemOrange, renderingMode: .alwaysOriginal)
            )
            let orchestrationItem = CPListItem(
                text: "Travel Orchestration",
                detailText: overview.navigationState?.routeHistory.isEmpty == false
                    ? "\(overview.navigationState?.routeHistory.count ?? 0) stored route(s) are ready to resume across surfaces."
                    : overview.navigationState?.recentDestinations.isEmpty == false
                    ? "Recent routes and preferred origin are ready for the next drive."
                    : "Planner continuity will grow as routes are previewed."
            )
            orchestrationItem.setImage(
                UIImage(systemName: "calendar.badge.clock")?
                    .withTintColor(.systemPurple, renderingMode: .alwaysOriginal)
            )
            sections.append(CPListSection(items: [originItem, plannerItem, orchestrationItem], header: RouteSectionHeader.tripSetup, sectionIndexTitle: nil))
            routeTemplate.updateSections(sections)
            refreshNavigationSurface()
        } catch {
            navigationSession?.cancelTrip()
            navigationSession = nil
            activeTrip = nil
            activeRouteChoice = nil
            activeRouteKey = nil
            mapTemplate.hideTripPreviews()
            updateNavigationControls()
            let item = CPListItem(text: "Couldn't load route planner", detailText: error.localizedDescription)
            routeTemplate.updateSections([CPListSection(items: [item])])
        }
    }

    private func updateNavigationControls() {
        let routesButton = CPBarButton(title: "Routes") { [weak self] _ in
            self?.showRouteChooser()
        }
        routesButton.buttonStyle = .rounded

        let talkButton = CPBarButton(title: "Talk") { [weak self] _ in
            self?.showConversationLane()
        }
        talkButton.buttonStyle = .rounded

        let intelButton = CPBarButton(title: "Intel") { [weak self] _ in
            self?.showIntelligenceLane()
        }
        intelButton.buttonStyle = .rounded

        let refreshImage = UIImage(systemName: "arrow.clockwise") ?? UIImage()
        let refreshButton = CPBarButton(image: refreshImage) { [weak self] _ in
            guard let self else { return }
            Task { await self.refreshAll() }
        }
        refreshButton.buttonStyle = .rounded

        mapTemplate.leadingNavigationBarButtons = [routesButton, talkButton]
        mapTemplate.trailingNavigationBarButtons = [intelButton, refreshButton]

        let routesMapButton = CPMapButton { [weak self] _ in
            self?.showRouteChooser()
        }
        routesMapButton.image = UIImage(systemName: "list.bullet.rectangle.portrait")

        let detailsMapButton = CPMapButton { [weak self] _ in
            self?.showActiveRouteDetail()
        }
        detailsMapButton.image = UIImage(systemName: "location.viewfinder")
        detailsMapButton.isHidden = currentRoute == nil

        mapTemplate.mapButtons = [routesMapButton, detailsMapButton]
    }

    private func refreshNavigationSurface() {
        updateNavigationControls()

        guard let route = currentRoute else {
            navigationSession?.cancelTrip()
            navigationSession = nil
            activeTrip = nil
            activeRouteChoice = nil
            activeRouteKey = nil
            mapTemplate.hideTripPreviews()
            return
        }

        let bundle = makeNavigationTripBundle(for: route)
        activeTrip = bundle.trip
        activeRouteChoice = bundle.routeChoice
        mapTemplate.hideTripPreviews()
        mapTemplate.update(
            bundle.tripEstimates,
            for: bundle.trip,
            with: route.hazardActive ? .orange : .green
        )

        let isSameRoute = activeRouteKey == bundle.routeKey
        if !isSameRoute {
            navigationSession?.cancelTrip()
            navigationSession = mapTemplate.startNavigationSession(for: bundle.trip)
            activeRouteKey = bundle.routeKey
        }

        guard let navigationSession else { return }
        navigationSession.add(bundle.maneuvers)
        navigationSession.upcomingManeuvers = bundle.maneuvers
        navigationSession.currentRoadNameVariants = currentRoadNameVariants(for: route)
        navigationSession.maneuverState = .initial
        if let firstManeuver = bundle.maneuvers.first,
           let firstEstimates = firstManeuver.initialTravelEstimates {
            navigationSession.updateEstimates(firstEstimates, for: firstManeuver)
        }
    }

    private func makeNavigationTripBundle(for route: NavigationRouteOverview) -> NavigationTripBundle {
        let summary = JarvisCarPlayPresentation.routeDetail(for: route)
        let routeChoice = CPRouteChoice(
            summaryVariants: [summary.isEmpty ? route.destination.label : summary],
            additionalInformationVariants: [route.summary.isEmpty ? "Smart navigation is ready." : route.summary],
            selectionSummaryVariants: ["Start navigation to \(route.destination.label)"]
        )

        let originCoordinate = CLLocationCoordinate2D(latitude: route.origin.lat, longitude: route.origin.lon)
        let destinationCoordinate = CLLocationCoordinate2D(latitude: route.destination.lat, longitude: route.destination.lon)

        let originPlacemark = MKPlacemark(coordinate: originCoordinate)
        let destinationPlacemark = MKPlacemark(coordinate: destinationCoordinate)
        let originMapItem = MKMapItem(placemark: originPlacemark)
        originMapItem.name = route.origin.label
        let destinationMapItem = MKMapItem(placemark: destinationPlacemark)
        destinationMapItem.name = route.destination.label

        let trip = CPTrip(origin: originMapItem, destination: destinationMapItem, routeChoices: [routeChoice])
        trip.destinationNameVariants = [route.destination.label]

        let tripEstimates = CPTravelEstimates(
            distanceRemaining: Measurement(
                value: route.route.distanceMiles ?? -1,
                unit: UnitLength.miles
            ),
            timeRemaining: TimeInterval((route.route.durationMinutes ?? -1) * 60)
        )

        let maneuvers = buildManeuvers(for: route)
        return NavigationTripBundle(
            trip: trip,
            routeChoice: routeChoice,
            tripEstimates: tripEstimates,
            maneuvers: maneuvers,
            routeKey: routeKey(for: route)
        )
    }

    private func buildManeuvers(for route: NavigationRouteOverview) -> [CPManeuver] {
        if route.route.steps.isEmpty {
            let maneuver = CPManeuver()
            maneuver.instructionVariants = ["Head toward \(route.destination.label)"]
            maneuver.dashboardInstructionVariants = maneuver.instructionVariants
            maneuver.notificationInstructionVariants = maneuver.instructionVariants
            maneuver.symbolImage = UIImage(systemName: "arrow.up")
            maneuver.dashboardSymbolImage = maneuver.symbolImage
            maneuver.notificationSymbolImage = maneuver.symbolImage
            maneuver.maneuverType = .startRoute
            maneuver.roadFollowingManeuverVariants = [route.destination.label]
            maneuver.initialTravelEstimates = CPTravelEstimates(
                distanceRemaining: Measurement(
                    value: route.route.distanceMiles ?? -1,
                    unit: UnitLength.miles
                ),
                timeRemaining: TimeInterval((route.route.durationMinutes ?? -1) * 60)
            )
            if route.hazardActive {
                maneuver.cardBackgroundColor = UIColor.systemOrange
            }
            return [maneuver]
        }

        return Array(route.route.steps.prefix(4)).map { step in
            let maneuver = CPManeuver()
            maneuver.instructionVariants = [step.instruction]
            maneuver.dashboardInstructionVariants = [step.instruction]
            maneuver.notificationInstructionVariants = [step.instruction]
            maneuver.symbolImage = UIImage(systemName: maneuverSymbolName(for: step))
            maneuver.dashboardSymbolImage = maneuver.symbolImage
            maneuver.notificationSymbolImage = maneuver.symbolImage
            maneuver.maneuverType = maneuverType(for: step)
            if !step.name.isEmpty {
                maneuver.roadFollowingManeuverVariants = [step.name]
            }
            maneuver.initialTravelEstimates = CPTravelEstimates(
                distanceRemaining: Measurement(
                    value: step.distanceMiles ?? route.route.distanceMiles ?? -1,
                    unit: UnitLength.miles
                ),
                timeRemaining: TimeInterval((step.durationMinutes ?? route.route.durationMinutes ?? -1) * 60)
            )
            if route.hazardActive {
                maneuver.cardBackgroundColor = UIColor.systemOrange
            }
            return maneuver
        }
    }

    private func currentRoadNameVariants(for route: NavigationRouteOverview) -> [String] {
        let road = route.route.steps.first(where: { !$0.name.isEmpty })?.name ?? route.destination.label
        return [road]
    }

    private func routeKey(for route: NavigationRouteOverview) -> String {
        "\(route.origin.label.lowercased())::\(route.destination.label.lowercased())"
    }

    private func maneuverType(for step: NavigationRouteStep) -> CPManeuverType {
        let maneuver = step.maneuver.lowercased()
        let modifier = step.modifier.lowercased()

        switch maneuver {
        case "arrive":
            return modifier.contains("left") ? .arriveAtDestinationLeft : modifier.contains("right") ? .arriveAtDestinationRight : .arriveAtDestination
        case "depart":
            return modifier.contains("uturn") ? .startRouteWithUTurn : .startRoute
        case "merge":
            return .changeHighway
        case "fork":
            return modifier.contains("left") ? .keepLeft : modifier.contains("right") ? .keepRight : .followRoad
        case "roundabout", "rotary":
            return .enterRoundabout
        default:
            if modifier.contains("uturn") {
                return .uTurn
            }
            if modifier.contains("sharp left") {
                return .sharpLeftTurn
            }
            if modifier.contains("sharp right") {
                return .sharpRightTurn
            }
            if modifier.contains("slight left") {
                return .slightLeftTurn
            }
            if modifier.contains("slight right") {
                return .slightRightTurn
            }
            if modifier.contains("left") {
                return .leftTurn
            }
            if modifier.contains("right") {
                return .rightTurn
            }
            if modifier.contains("straight") {
                return .straightAhead
            }
            return .followRoad
        }
    }

    private func maneuverSymbolName(for step: NavigationRouteStep) -> String {
        let modifier = step.modifier.lowercased()
        let maneuver = step.maneuver.lowercased()

        if modifier.contains("uturn") {
            return "arrow.uturn.backward"
        }
        if modifier.contains("sharp left") {
            return "arrow.turn.up.left"
        }
        if modifier.contains("sharp right") {
            return "arrow.turn.up.right"
        }
        if modifier.contains("slight left") {
            return "arrow.up.left"
        }
        if modifier.contains("slight right") {
            return "arrow.up.right"
        }
        if modifier.contains("left") {
            return "arrow.turn.up.left"
        }
        if modifier.contains("right") {
            return "arrow.turn.up.right"
        }
        if maneuver == "arrive" {
            return "flag.checkered"
        }
        if maneuver == "merge" {
            return "arrow.merge"
        }
        return "arrow.up"
    }

    private func showRouteChooser() {
        interfaceController.pushTemplate(routeTemplate, animated: true, completion: nil)
    }

    private func showActiveRouteDetail() {
        if let activeRouteTemplate {
            interfaceController.pushTemplate(activeRouteTemplate, animated: true, completion: nil)
            return
        }
        guard let route = currentRoute else { return }
        Task {
            await presentRouteExperience(
                origin: route.origin.label,
                destination: route.destination.label,
                persistSelection: false
            )
        }
    }

    private func showConversationLane() {
        interfaceController.pushTemplate(conversationTemplate, animated: true, completion: nil)
    }

    private func showIntelligenceLane() {
        interfaceController.pushTemplate(intelligenceTemplate, animated: true, completion: nil)
    }

    private func loadPublishing() async {
        do {
            let overview = try await client.fetchPublishing()
            publishReviews = overview.pendingReviews
            publishQueue = JarvisCarPlayPresentation.publishQueue(from: overview)
            publishLaunchWorkspace = overview.launchWorkspace
            publishHistory = overview.launchHistory.items

            var sections: [CPListSection] = []
            if let launchControl = overview.launchControl {
                let detail = [
                    launchControl.phase.replacingOccurrences(of: "_", with: " ").capitalized,
                    launchControl.status.capitalized,
                    launchControl.nextAction,
                ]
                    .filter { !$0.isEmpty }
                    .joined(separator: " · ")
                let item = CPListItem(text: launchControl.title, detailText: detail)
                item.setImage(
                    UIImage(systemName: "shippingbox.fill")?
                        .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
                )
                sections.append(CPListSection(items: [item], header: "Launch Control", sectionIndexTitle: nil))
            }

            if let workspace = overview.launchWorkspace {
                let nextStep = workspace.checklist.first(where: { !$0.completed })
                let item = CPListItem(
                    text: nextStep?.label ?? "Launch checklist complete",
                    detailText: nextStep != nil
                        ? "\(workspace.checklistProgress) complete · Tap to mark the next step done."
                        : "\(workspace.checklistProgress) complete · Nothing is waiting in the launch checklist."
                )
                item.setImage(
                    UIImage(systemName: nextStep == nil ? "checkmark.seal.fill" : "checkmark.circle")?
                        .withTintColor(nextStep == nil ? .systemGreen : .systemOrange, renderingMode: .alwaysOriginal)
                )
                sections.append(CPListSection(items: [item], header: "Launch Checklist", sectionIndexTitle: nil))
            }

            let handoffItem = CPListItem(
                text: "Ghostwritr Publish Handoff",
                detailText: overview.pendingReviewsCount > 0
                    ? "\(overview.pendingReviewsCount) review item(s) waiting with live launch continuity."
                    : "Queue is clear and launch posture is stable."
            )
            handoffItem.setImage(
                UIImage(systemName: "shippingbox.fill")?
                    .withTintColor(.systemOrange, renderingMode: .alwaysOriginal)
            )
            sections.insert(CPListSection(items: [handoffItem], header: "Handoff State", sectionIndexTitle: nil), at: 0)

            if publishQueue.isEmpty {
                let item = CPListItem(text: "No reviews waiting", detailText: "Publishing queue is clear right now.")
                item.setImage(
                    UIImage(systemName: "checkmark.circle.fill")?
                        .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
                )
                sections.append(CPListSection(items: [item], header: "Review Queue", sectionIndexTitle: nil))
            } else {
                let items = publishQueue.map { review in
                    let item = CPListItem(text: review.title, detailText: review.detail)
                    item.setImage(
                        UIImage(systemName: "doc.text.magnifyingglass")?
                            .withTintColor(.systemOrange, renderingMode: .alwaysOriginal)
                    )
                    return item
                }
                sections.append(CPListSection(items: items, header: "Review Queue", sectionIndexTitle: nil))
            }

            if !overview.actionItems.isEmpty {
                let items = overview.actionItems.prefix(3).map { action in
                    let item = CPListItem(text: action.title, detailText: action.detail)
                    item.setImage(UIImage(systemName: "sparkles"))
                    return item
                }
                sections.append(CPListSection(items: items, header: "Launch Ops", sectionIndexTitle: nil))
            }

            if !publishHistory.isEmpty {
                let items = publishHistory.prefix(3).map { history in
                    let item = CPListItem(text: history.title, detailText: history.detail.isEmpty ? history.statusLabel : history.detail)
                    item.setImage(
                        UIImage(systemName: "clock.arrow.trianglehead.counterclockwise.rotate.90")?
                            .withTintColor(.systemTeal, renderingMode: .alwaysOriginal)
                    )
                    return item
                }
                sections.append(CPListSection(items: items, header: "Launch History", sectionIndexTitle: nil))
            }

            publishTemplate.updateSections(sections)
        } catch {
            let item = CPListItem(text: "Couldn't load publish queue", detailText: error.localizedDescription)
            publishTemplate.updateSections([CPListSection(items: [item])])
        }
    }

    private func loadOps() async {
        do {
            let overview = try await client.fetchCarPlayOps()
            opsOverview = overview

            var sections: [CPListSection] = []

            let currentFocus = overview.currentFocus
            let commandItem = CPListItem(
                text: "Catalyst Command Deck",
                detailText: "\(overview.counts.approvalCount) approvals · \(overview.counts.recoveryCaseCount) recovery cases · \(overview.counts.agentOpsCount) agent ops · \(overview.counts.supervisionCount) supervision review(s)"
            )
            commandItem.setImage(
                UIImage(systemName: "gauge.with.dots.needle.67percent")?
                    .withTintColor(.systemIndigo, renderingMode: .alwaysOriginal)
            )
            let focusItem = CPListItem(
                text: "Shared Focus: \(currentFocus.module)",
                detailText: currentFocus.reason.isEmpty ? "Shared progress continuity is active." : currentFocus.reason
            )
            focusItem.setImage(
                UIImage(systemName: "scope")?
                    .withTintColor(.systemOrange, renderingMode: .alwaysOriginal)
            )
            sections.append(CPListSection(items: [commandItem, focusItem], header: "1. Command Chamber", sectionIndexTitle: nil))

            let focusItems = overview.focusCandidates.map { candidate in
                let item = CPListItem(text: candidate.label, detailText: candidate.module)
                item.setImage(
                    UIImage(systemName: "arrow.up.forward.app.fill")?
                        .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
                )
                return item
            }
            sections.append(CPListSection(items: focusItems, header: "2. Focus Lanes", sectionIndexTitle: nil))

            let recoveryItems: [CPListItem]
            if overview.recoveryCases.isEmpty {
                let item = CPListItem(text: "Recovery stack is steady", detailText: "No durable cases need attention right now.")
                item.setImage(
                    UIImage(systemName: "checkmark.shield.fill")?
                        .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
                )
                recoveryItems = [item]
            } else {
                recoveryItems = overview.recoveryCases.prefix(4).map { entry in
                    let countLabel = entry.executionCount > 0 ? " · \(entry.executionCount)x run" : ""
                    let item = CPListItem(text: "\(entry.statusLabel): \(entry.title)", detailText: entry.detail + countLabel)
                    item.setImage(
                        UIImage(systemName: entry.statusLabel == "Resolved" ? "checkmark.circle.fill" : "waveform.path.ecg")?
                            .withTintColor(entry.statusLabel == "Resolved" ? .systemGreen : .systemOrange, renderingMode: .alwaysOriginal)
                    )
                    return item
                }
            }
            let approvalItems: [CPListItem]
            if overview.approvals.isEmpty {
                let item = CPListItem(text: "Approval lane is clear", detailText: "Nothing is waiting for a review tap.")
                item.setImage(
                    UIImage(systemName: "checkmark.circle.fill")?
                        .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
                )
                approvalItems = [item]
            } else {
                approvalItems = overview.approvals.prefix(4).map { approval in
                    let item = CPListItem(text: approval.title, detailText: "\(approval.agent) · \(approval.risk.capitalized) risk")
                    item.setImage(riskImage(for: approval.risk))
                    return item
                }
            }
            sections.append(CPListSection(items: approvalItems, header: "3. Approvals", sectionIndexTitle: nil))

            sections.append(CPListSection(items: recoveryItems, header: "4. Recovery", sectionIndexTitle: nil))

            let agentOpsItems: [CPListItem]
            if overview.agentOps.isEmpty {
                let item = CPListItem(text: "No agent push needed", detailText: "Agent runs are steady from the in-car lane.")
                item.setImage(
                    UIImage(systemName: "person.crop.circle.badge.checkmark")?
                        .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
                )
                agentOpsItems = [item]
            } else {
                agentOpsItems = overview.agentOps.prefix(4).map { agent in
                    let detail = [agent.assignment, agent.attentionReason.isEmpty ? agent.purpose : agent.attentionReason]
                        .filter { !$0.isEmpty }
                        .joined(separator: " · ")
                    let item = CPListItem(text: "\(agent.name) · \(agent.status.capitalized)", detailText: detail)
                    item.setImage(
                        UIImage(systemName: "person.2.badge.gearshape.fill")?
                            .withTintColor(.systemTeal, renderingMode: .alwaysOriginal)
                    )
                    return item
                }
            }
            sections.append(CPListSection(items: agentOpsItems, header: "5. Agent Ops", sectionIndexTitle: nil))

            let supervisionItems: [CPListItem]
            if overview.supervisionItems.isEmpty {
                let item = CPListItem(text: "No supervision review waiting", detailText: "Bounded-autonomy reviews are clear right now.")
                item.setImage(
                    UIImage(systemName: "eye.circle.fill")?
                        .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
                )
                supervisionItems = [item]
            } else {
                supervisionItems = overview.supervisionItems.prefix(4).map { review in
                    let item = CPListItem(text: review.title, detailText: "\(review.agent) · \(review.risk.capitalized) risk")
                    item.setImage(riskImage(for: review.risk))
                    return item
                }
            }
            sections.append(CPListSection(items: supervisionItems, header: "6. Supervision", sectionIndexTitle: nil))

            let huddleSummary = overview.huddleSummary
            let huddleSummaryItem = CPListItem(
                text: "Huddle Chamber",
                detailText: huddleSummary.headline
            )
            huddleSummaryItem.setImage(
                UIImage(systemName: "person.3.sequence.fill")?
                    .withTintColor(.systemYellow, renderingMode: .alwaysOriginal)
            )
            let huddlePartyItem = CPListItem(
                text: huddleSummary.partyModeStatus.lowercased() == "running" ? "Agents Working Overnight" : "Wake Agents",
                detailText: huddleSummary.partyModeStatus.lowercased() == "running"
                    ? "Party mode is running. Keep the lane warm and review queued ideas."
                    : "Start overnight research from the in-car Huddle lane."
            )
            huddlePartyItem.setImage(
                UIImage(systemName: huddleSummary.partyModeStatus.lowercased() == "running" ? "moon.stars.fill" : "sparkles")?
                    .withTintColor(.systemPurple, renderingMode: .alwaysOriginal)
            )
            sections.append(CPListSection(items: [huddleSummaryItem, huddlePartyItem], header: "7. Huddle Chamber", sectionIndexTitle: nil))

            let huddleIdeaItems: [CPListItem]
            if overview.huddleIdeas.isEmpty {
                let item = CPListItem(text: "No huddle ideas waiting", detailText: "Capture ideas on desktop or phone and triage them from CarPlay.")
                item.setImage(
                    UIImage(systemName: "lightbulb.slash.fill")?
                        .withTintColor(.systemGray, renderingMode: .alwaysOriginal)
                )
                huddleIdeaItems = [item]
            } else {
                huddleIdeaItems = overview.huddleIdeas.prefix(4).map { idea in
                    let item = CPListItem(
                        text: idea.text,
                        detailText: "\(idea.domain.capitalized) · \(idea.status.replacingOccurrences(of: "_", with: " ").capitalized)"
                    )
                    item.setImage(
                        UIImage(systemName: idea.status.lowercased() == "researching" ? "waveform.path.ecg" : "lightbulb.max.fill")?
                            .withTintColor(idea.status.lowercased() == "researching" ? .systemPurple : .systemOrange, renderingMode: .alwaysOriginal)
                    )
                    return item
                }
            }
            sections.append(CPListSection(items: huddleIdeaItems, header: "8. Huddle Ideas", sectionIndexTitle: nil))

            let chronicleSummary = overview.chronicleSummary
            let chronicleSummaryItem = CPListItem(
                text: "Legacy Chamber",
                detailText: chronicleSummary.headline
            )
            chronicleSummaryItem.setImage(
                UIImage(systemName: "book.closed.fill")?
                    .withTintColor(.systemYellow, renderingMode: .alwaysOriginal)
            )
            let chroniclePromptItem = CPListItem(
                text: chronicleSummary.latestTitle.isEmpty ? "No Legacy thread ready" : chronicleSummary.latestTitle,
                detailText: chronicleSummary.studyTitle.isEmpty
                    ? "\(chronicleSummary.activePrayerCount) active prayer(s) · \(chronicleSummary.reviewCount) review thread(s)"
                    : "\(chronicleSummary.studyTitle) · \(chronicleSummary.reviewCount) review thread(s)"
            )
            chroniclePromptItem.setImage(
                UIImage(systemName: "text.book.closed.fill")?
                    .withTintColor(.systemOrange, renderingMode: .alwaysOriginal)
            )
            sections.append(CPListSection(items: [chronicleSummaryItem, chroniclePromptItem], header: "9. Legacy Chamber", sectionIndexTitle: nil))

            let chronicleReviewItems: [CPListItem]
            if overview.chronicleReviews.isEmpty {
                let item = CPListItem(text: "No Legacy review waiting", detailText: "Move a memory thread into study or family handoff from the phone.")
                item.setImage(
                    UIImage(systemName: "checkmark.circle.fill")?
                        .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
                )
                chronicleReviewItems = [item]
            } else {
                chronicleReviewItems = overview.chronicleReviews.prefix(4).map { review in
                    let item = CPListItem(
                        text: review.entryTitle,
                        detailText: "\(review.reviewStatusLabel) · \(review.entryType.capitalized)"
                    )
                    item.setImage(
                        UIImage(systemName: review.reviewStatus == "resolved" ? "checkmark.seal.fill" : "book.pages.fill")?
                            .withTintColor(review.reviewStatus == "resolved" ? .systemGreen : .systemBlue, renderingMode: .alwaysOriginal)
                    )
                    return item
                }
            }
            sections.append(CPListSection(items: chronicleReviewItems, header: "10. Legacy Reviews", sectionIndexTitle: nil))

            let missionHeadline = overview.missionSummary.headline.isEmpty
                ? "\(overview.missionSummary.activeCount) active mission(s) are flowing through JARVIS."
                : overview.missionSummary.headline
            let missionItem = CPListItem(
                text: "Mission Pressure",
                detailText: missionHeadline
            )
            missionItem.setImage(
                UIImage(systemName: "flag.2.crossed.fill")?
                    .withTintColor(.systemRed, renderingMode: .alwaysOriginal)
            )
            let agentItem = CPListItem(
                text: "Agent Posture",
                detailText: "\(overview.agentSummary.awakeCount) awake · \(overview.agentSummary.blockedCount) blocked · \(overview.agentSummary.totalCount) tracked"
            )
            agentItem.setImage(
                UIImage(systemName: "person.3.fill")?
                    .withTintColor(.systemTeal, renderingMode: .alwaysOriginal)
            )
            let activityItems: [CPListItem]
            if overview.recentActivity.isEmpty {
                activityItems = [CPListItem(text: "No recent continuity yet", detailText: "Ops actions will echo back here when they happen.")]
            } else {
                activityItems = overview.recentActivity.prefix(4).map { entry in
                    let item = CPListItem(text: entry.title, detailText: [entry.detail, entry.routeLabel].filter { !$0.isEmpty }.joined(separator: " · "))
                    item.setImage(
                        UIImage(systemName: "clock.arrow.circlepath")?
                            .withTintColor(.systemGray, renderingMode: .alwaysOriginal)
                    )
                    return item
                }
            }
            sections.append(CPListSection(items: [missionItem, agentItem], header: "11. Mission Pressure", sectionIndexTitle: nil))
            sections.append(CPListSection(items: activityItems, header: "12. Recent Continuity", sectionIndexTitle: nil))

            opsTemplate.updateSections(sections)
        } catch {
            let item = CPListItem(text: "Couldn't load ops deck", detailText: error.localizedDescription)
            opsTemplate.updateSections([CPListSection(items: [item])])
        }
    }

    private func icon(for source: CarPlayNavigationChoice.Source) -> UIImage? {
        let name: String
        let tint: UIColor
        switch source {
        case .saved:
            name = "house.fill"
            tint = .systemBlue
        case .favorite:
            name = "star.fill"
            tint = .systemOrange
        case .recent:
            name = "clock.fill"
            tint = .systemTeal
        case .routeHistory:
            name = "arrow.triangle.swap"
            tint = .systemPurple
        }
        return UIImage(systemName: name)?.withTintColor(tint, renderingMode: .alwaysOriginal)
    }

    private func riskImage(for risk: String) -> UIImage? {
        switch risk {
        case "high":
            return UIImage(systemName: "exclamationmark.triangle.fill")?
                .withTintColor(.systemRed, renderingMode: .alwaysOriginal)
        case "medium":
            return UIImage(systemName: "exclamationmark.circle.fill")?
                .withTintColor(.systemOrange, renderingMode: .alwaysOriginal)
        default:
            return UIImage(systemName: "info.circle.fill")?
                .withTintColor(.systemYellow, renderingMode: .alwaysOriginal)
        }
    }

    func listTemplate(
        _ listTemplate: CPListTemplate,
        didSelect item: CPListItem,
        completionHandler: @escaping () -> Void
    ) {
        guard let indexPath = indexPath(of: item, in: listTemplate) else {
            completionHandler()
            return
        }

        if listTemplate === needsTemplate {
            guard indexPath.item < pendingNeeds.count else {
                completionHandler()
                return
            }
            presentApproveAlert(for: pendingNeeds[indexPath.item], completion: completionHandler)
            return
        }

        if listTemplate === routeTemplate {
            Task {
                await handleRouteSelection(indexPath: indexPath)
                completionHandler()
            }
            return
        }

        if listTemplate === conversationTemplate {
            Task {
                await handleConversationSelection(indexPath: indexPath)
                completionHandler()
            }
            return
        }

        if listTemplate === activeRouteTemplate {
            Task {
                await handleRouteDetailSelection(indexPath: indexPath)
                completionHandler()
            }
            return
        }

        if listTemplate === activeConversationTemplate {
            Task {
                await handleConversationFollowUpSelection(indexPath: indexPath)
                completionHandler()
            }
            return
        }

        if listTemplate === intelligenceTemplate {
            let needsSectionIndex = intelligenceTemplate.sections.firstIndex { $0.header == IntelligenceSectionHeader.needsYou }
            if let needsSectionIndex, indexPath.section == needsSectionIndex, indexPath.item < intelligenceActions.count {
                switch intelligenceActions[indexPath.item] {
                case .need(let need):
                    presentApproveAlert(for: need, completion: completionHandler)
                case .publishReview(let review):
                    presentPublishReviewAlert(for: review, completion: completionHandler)
                }
                return
            }
        }

        if listTemplate === publishTemplate {
            let checklistSectionIndex = publishTemplate.sections.firstIndex { $0.header == "Launch Checklist" }
            if let checklistSectionIndex, indexPath.section == checklistSectionIndex {
                presentPublishChecklistAlert(completion: completionHandler)
                return
            }
            let queueSectionIndex = publishTemplate.sections.firstIndex { $0.header == "Review Queue" } ?? 0
            guard indexPath.section == queueSectionIndex, indexPath.item < publishReviews.count else {
                completionHandler()
                return
            }
            presentPublishReviewAlert(for: publishReviews[indexPath.item], completion: completionHandler)
            return
        }

        if listTemplate === opsTemplate {
            Task {
                await handleOpsSelection(indexPath: indexPath)
                completionHandler()
            }
            return
        }

        completionHandler()
    }

    private func indexPath(of item: CPListItem, in template: CPListTemplate) -> (section: Int, item: Int)? {
        for (sectionIndex, section) in template.sections.enumerated() {
            for (itemIndex, candidate) in section.items.enumerated() where candidate === item {
                return (sectionIndex, itemIndex)
            }
        }
        return nil
    }

    private func handleRouteSelection(indexPath: (section: Int, item: Int)) async {
        let routeSections = routeTemplate.sections
        let upcomingSectionIndex = routeSections.firstIndex { $0.header == RouteSectionHeader.nextTurns }
        if routeCurrentItemSelectable,
           let upcomingSectionIndex,
           indexPath.section == upcomingSectionIndex,
           indexPath.item == 0,
           let route = currentRoute {
            let origin = route.origin.label
            let destination = route.destination.label
            await presentRouteExperience(origin: origin, destination: destination, persistSelection: false)
            return
        }

        let destinationSectionIndex = routeSections.firstIndex { $0.header == RouteSectionHeader.destinations }
        guard indexPath.section == destinationSectionIndex, indexPath.item < navigationChoices.count else {
            return
        }

        let choice = navigationChoices[indexPath.item]
        guard let overview = navigationOverview else { return }
        let origin = JarvisCarPlayPresentation.preferredOriginLabel(from: overview)

        do {
            if choice.source == .routeHistory,
               let routeID = choice.id.split(separator: ":").dropFirst().first.map(String.init),
               !routeID.isEmpty {
                _ = try await client.resumeNavigationHistoryRoute(routeID)
            } else {
                let currentState = try await client.fetchNavigationState()
                let updatedRecent = mergeRecentDestinations(
                    choice.destination,
                    into: currentState.recentDestinations
                )
                let patch = NavigationStatePatch(
                    recentDestinations: updatedRecent,
                    selectedOriginMode: currentState.selectedOriginMode,
                    selectedSavedLocationID: currentState.selectedSavedLocationID,
                    lastRoute: NavigationLastRoute(origin: origin, destination: choice.destination)
                )
                _ = try await client.updateNavigationState(patch)
            }
        } catch {
            // Continue into route presentation even if persistence fails.
        }

        await presentRouteExperience(origin: origin, destination: choice.destination, persistSelection: true)
    }

    private func handleRouteDetailSelection(indexPath: (section: Int, item: Int)) async {
        guard let template = activeRouteTemplate else { return }
        let stopSectionIndex = template.sections.firstIndex { $0.header == RouteSectionHeader.smartStops }
        guard let stopSectionIndex, indexPath.section == stopSectionIndex, indexPath.item < activeRouteStops.count else {
            return
        }
        let stop = activeRouteStops[indexPath.item]
        presentStopDetail(stop)
    }

    private func handleConversationSelection(indexPath: (section: Int, item: Int)) async {
        let promptSectionIndex = conversationTemplate.sections.firstIndex { $0.header == ConversationSectionHeader.prompts }
        guard let promptSectionIndex, indexPath.section == promptSectionIndex, indexPath.item < conversationPrompts.count else {
            return
        }
        await sendConversationPrompt(conversationPrompts[indexPath.item])
    }

    private func handleConversationFollowUpSelection(indexPath: (section: Int, item: Int)) async {
        guard let template = activeConversationTemplate else { return }
        let followUpSectionIndex = template.sections.firstIndex { $0.header == ConversationSectionHeader.followUp }
        guard let followUpSectionIndex, indexPath.section == followUpSectionIndex, indexPath.item < activeConversationFollowUps.count else {
            return
        }
        await sendConversationPrompt(activeConversationFollowUps[indexPath.item])
    }

    private func sendConversationPrompt(_ prompt: String) async {
        do {
            let response = try await client.speak(
                text: prompt,
                actorId: "chris",
                conversationId: activeConversationId.isEmpty ? nil : activeConversationId
            )
            if !response.conversationId.isEmpty {
                activeConversationId = response.conversationId
            }
            await loadConversation()
            await loadIntelligence()
            presentConversationResponse(prompt: prompt, response: response)
        } catch {
            let alert = CPAlertTemplate(
                titleVariants: ["Couldn't reach JARVIS"],
                actions: [CPAlertAction(title: error.localizedDescription, style: .cancel) { _ in }]
            )
            interfaceController.presentTemplate(alert, animated: true, completion: nil)
        }
    }

    private func presentConversationResponse(prompt: String, response: SpeakResponse) {
        let promptItem = CPListItem(text: "You asked", detailText: prompt)
        promptItem.setImage(
            UIImage(systemName: "person.fill")?
                .withTintColor(.systemGray, renderingMode: .alwaysOriginal)
        )
        let replyItem = CPListItem(
            text: response.agent.isEmpty ? "JARVIS" : response.agent,
            detailText: response.displayText.isEmpty ? response.response : response.displayText
        )
        replyItem.setImage(
            UIImage(systemName: "brain.head.profile")?
                .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
        )

        activeConversationFollowUps = mergedConversationPrompts(
            primary: response.followUpSuggestions,
            fallback: fallbackConversationPrompts()
        )
        let followUpItems = activeConversationFollowUps.map { suggestion in
            let item = CPListItem(text: suggestion, detailText: "Keep the thread moving")
            item.setImage(
                UIImage(systemName: "arrowshape.turn.up.right.circle.fill")?
                    .withTintColor(.systemPurple, renderingMode: .alwaysOriginal)
            )
            return item
        }

        let template = CPListTemplate(
            title: "JARVIS",
            sections: [
                CPListSection(items: [promptItem, replyItem], header: ConversationSectionHeader.status, sectionIndexTitle: nil),
                CPListSection(items: followUpItems, header: ConversationSectionHeader.followUp, sectionIndexTitle: nil),
            ]
        )
        template.delegate = self
        activeConversationTemplate = template
        interfaceController.pushTemplate(template, animated: true, completion: nil)
    }

    private func handleOpsSelection(indexPath: (section: Int, item: Int)) async {
        guard let overview = opsOverview else { return }
        let focusSectionIndex = opsTemplate.sections.firstIndex { $0.header == "2. Focus Lanes" }
        if let focusSectionIndex, indexPath.section == focusSectionIndex, indexPath.item < overview.focusCandidates.count {
            let candidate = overview.focusCandidates[indexPath.item]
            presentOpsFocusAlert(for: candidate)
            return
        }
        let approvalSectionIndex = opsTemplate.sections.firstIndex { $0.header == "3. Approvals" }
        if let approvalSectionIndex, indexPath.section == approvalSectionIndex, indexPath.item < overview.approvals.count {
            presentOpsApprovalAlert(for: overview.approvals[indexPath.item])
            return
        }
        let agentSectionIndex = opsTemplate.sections.firstIndex { $0.header == "5. Agent Ops" }
        if let agentSectionIndex, indexPath.section == agentSectionIndex, indexPath.item < overview.agentOps.count {
            presentCarPlayAgentAlert(for: overview.agentOps[indexPath.item])
            return
        }
        let supervisionSectionIndex = opsTemplate.sections.firstIndex { $0.header == "6. Supervision" }
        if let supervisionSectionIndex, indexPath.section == supervisionSectionIndex, indexPath.item < overview.supervisionItems.count {
            presentCarPlaySupervisionAlert(for: overview.supervisionItems[indexPath.item])
            return
        }
        let huddleSectionIndex = opsTemplate.sections.firstIndex { $0.header == "7. Huddle Chamber" }
        if let huddleSectionIndex, indexPath.section == huddleSectionIndex {
            presentCarPlayHuddleSummaryAlert(summary: overview.huddleSummary)
            return
        }
        let huddleIdeasSectionIndex = opsTemplate.sections.firstIndex { $0.header == "8. Huddle Ideas" }
        if let huddleIdeasSectionIndex, indexPath.section == huddleIdeasSectionIndex, indexPath.item < overview.huddleIdeas.count {
            presentCarPlayHuddleIdeaAlert(for: overview.huddleIdeas[indexPath.item])
            return
        }
        let chronicleSectionIndex = opsTemplate.sections.firstIndex { $0.header == "9. Legacy Chamber" }
        if let chronicleSectionIndex, indexPath.section == chronicleSectionIndex {
            presentCarPlayChronicleSummaryAlert(summary: overview.chronicleSummary)
            return
        }
        let chronicleReviewSectionIndex = opsTemplate.sections.firstIndex { $0.header == "10. Legacy Reviews" }
        if let chronicleReviewSectionIndex, indexPath.section == chronicleReviewSectionIndex, indexPath.item < overview.chronicleReviews.count {
            presentCarPlayChronicleReviewAlert(for: overview.chronicleReviews[indexPath.item])
        }
    }

    private func mergeRecentDestinations(_ destination: String, into existing: [String]) -> [String] {
        let normalized = destination.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalized.isEmpty else { return existing }
        let filtered = existing.filter { $0.caseInsensitiveCompare(normalized) != .orderedSame }
        return Array(([normalized] + filtered).prefix(8))
    }

    private func fallbackConversationPrompts() -> [String] {
        if let route = currentRoute {
            var prompts = [
                "What should I know about this drive?",
                "What matters before I arrive?",
            ]
            if route.hazardActive {
                prompts.append("Should I reroute?")
            }
            prompts.append(activeRouteStops.isEmpty ? "Where should we stop if needed?" : "Which stop makes the most sense?")
            return prompts
        }
        return [
            "Help me think through this drive.",
            "What matters before I head out?",
            "What should I handle on the way?",
        ]
    }

    private func mergedConversationPrompts(primary: [String], fallback: [String], limit: Int = 5) -> [String] {
        var seen = Set<String>()
        var merged: [String] = []
        for candidate in primary + fallback {
            let trimmed = candidate.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty else { continue }
            let key = trimmed.lowercased()
            guard !seen.contains(key) else { continue }
            seen.insert(key)
            merged.append(trimmed)
            if merged.count == limit {
                break
            }
        }
        return merged
    }

    private func presentRouteExperience(origin: String, destination: String, persistSelection: Bool) async {
        do {
            let route = try await client.fetchNavigationRoute(origin: origin, destination: destination)
            let stops = try await client.fetchNavigationStops(origin: origin, destination: destination)
            currentRoute = route
            activeRouteStops = Array(stops.sections.flatMap(\.items).prefix(6))
            await loadConversation()
            await loadIntelligence()
            refreshNavigationSurface()

            var sections: [CPListSection] = []
            let summaryItem = CPListItem(
                text: route.route.steps.first?.instruction.isEmpty == false ? route.route.steps.first?.instruction ?? "\(route.origin.label) -> \(route.destination.label)" : "\(route.origin.label) -> \(route.destination.label)",
                detailText: [route.summary, JarvisCarPlayPresentation.routeDetail(for: route)]
                    .filter { !$0.isEmpty }
                    .joined(separator: " · ")
            )
            summaryItem.setImage(
                UIImage(systemName: persistSelection ? "location.fill" : "location.circle.fill")?
                    .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
            )
            let recommendationItem = CPListItem(
                text: "Recommended Next Action",
                detailText: route.hazardActive
                    ? "Review hazards and ask for voice guidance before leaving."
                    : "Leave on schedule and keep smart stops ready."
            )
            recommendationItem.setImage(
                UIImage(systemName: "checkmark.shield.fill")?
                    .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
            )
            sections.append(CPListSection(items: [summaryItem, recommendationItem], header: RouteSectionHeader.activeRoute, sectionIndexTitle: nil))

            if !route.route.steps.isEmpty {
                let stepItems = route.route.steps.prefix(4).map { step in
                    let detail = [
                        step.instruction,
                        step.distanceMiles.map { String(format: "%.1f mi", $0) } ?? "",
                    ]
                        .filter { !$0.isEmpty }
                        .joined(separator: " · ")
                    let item = CPListItem(text: step.name.isEmpty ? "Next maneuver" : step.name, detailText: detail)
                    item.setImage(UIImage(systemName: "arrow.turn.up.right"))
                    return item
                }
                sections.append(CPListSection(items: stepItems, header: RouteSectionHeader.nextTurns, sectionIndexTitle: nil))
            }

            let consultationItem = CPListItem(
                text: "Voice Navigation Consultation",
                detailText: route.hazardActive
                    ? "Ask JARVIS whether to leave now and how weather pressure changes the route."
                    : "Hands-free guidance is clear. JARVIS can answer timing and stop questions."
            )
            consultationItem.setImage(
                UIImage(systemName: "waveform")?
                    .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
            )
            let intelligenceItem = CPListItem(
                text: "Route Intelligence",
                detailText: JarvisCarPlayPresentation.routeDetail(for: route)
            )
            intelligenceItem.setImage(
                UIImage(systemName: "cloud.sun.rain.fill")?
                    .withTintColor(.systemTeal, renderingMode: .alwaysOriginal)
            )
            let liveViewItem = CPListItem(
                text: "Drive Focus",
                detailText: "Focused guidance keeps the next turn easy to scan."
            )
            liveViewItem.setImage(
                UIImage(systemName: "viewfinder.circle")?
                    .withTintColor(.systemPurple, renderingMode: .alwaysOriginal)
            )
            sections.append(CPListSection(items: [consultationItem, liveViewItem], header: RouteSectionHeader.guidance, sectionIndexTitle: nil))

            let destinationItem = CPListItem(
                text: route.destination.label,
                detailText: JarvisCarPlayPresentation.routeDetail(for: route)
            )
            destinationItem.setImage(
                UIImage(systemName: "flag.checkered.2.crossed")?
                    .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
            )
            sections.append(CPListSection(items: [destinationItem], header: RouteSectionHeader.destinations, sectionIndexTitle: nil))

            if activeRouteStops.isEmpty {
                let item = CPListItem(text: "No smart stops surfaced", detailText: "Try a different destination from the phone app.")
                sections.append(CPListSection(items: [item], header: RouteSectionHeader.smartStops, sectionIndexTitle: nil))
            } else {
                let items = activeRouteStops.map { stop in
                    let detail = [
                        stop.address,
                        stop.routeMileMarker.map { String(format: "mile %.0f", $0) } ?? "",
                        stop.distanceFromRoute.map { String(format: "+%.1f mi detour", $0) } ?? "",
                    ]
                        .filter { !$0.isEmpty }
                        .joined(separator: " · ")
                    let item = CPListItem(text: stop.name, detailText: detail)
                    item.setImage(UIImage(systemName: "mappin.and.ellipse"))
                    return item
                }
                sections.append(CPListSection(items: items, header: RouteSectionHeader.smartStops, sectionIndexTitle: nil))
            }

            sections.append(CPListSection(items: [intelligenceItem], header: RouteSectionHeader.tripSetup, sectionIndexTitle: nil))

            let detailTemplate = CPListTemplate(title: destination, sections: sections)
            detailTemplate.delegate = self
            activeRouteTemplate = detailTemplate
            interfaceController.pushTemplate(detailTemplate, animated: true, completion: nil)
        } catch {
            let alert = CPAlertTemplate(
                titleVariants: ["Unable to load route"],
                actions: [CPAlertAction(title: error.localizedDescription, style: .cancel) { _ in }]
            )
            interfaceController.presentTemplate(alert, animated: true, completion: nil)
        }
    }

    func mapTemplateDidCancelNavigation(_ mapTemplate: CPMapTemplate) {
        navigationSession = nil
        activeTrip = nil
        activeRouteChoice = nil
        activeRouteKey = nil
        updateNavigationControls()
    }

    private func presentStopDetail(_ stop: NavigationStop) {
        let detailItems = [
            CPListItem(text: "Address", detailText: stop.address.isEmpty ? "No address available" : stop.address),
            CPListItem(
                text: "Detour",
                detailText: stop.distanceFromRoute.map { String(format: "%.1f mi off route", $0) } ?? "Minimal detour"
            ),
            CPListItem(
                text: "Rating",
                detailText: stop.rating.map { String(format: "%.1f", $0) } ?? "No rating"
            ),
        ]
        let detailTemplate = CPListTemplate(
            title: stop.name,
            sections: [CPListSection(items: detailItems, header: "Stop Detail", sectionIndexTitle: nil)]
        )
        interfaceController.pushTemplate(detailTemplate, animated: true, completion: nil)
    }

    private func presentApproveAlert(
        for need: NeedsItem,
        completion: @escaping () -> Void
    ) {
        let approveAction = CPAlertAction(title: "Approve", style: .default) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.approve(requestId: need.id)
                await self.loadNeeds()
            }
        }
        let cancelAction = CPAlertAction(title: "Cancel", style: .cancel) { _ in }
        let alert = CPAlertTemplate(titleVariants: [need.text], actions: [approveAction, cancelAction])
        interfaceController.presentTemplate(alert, animated: true) { _, _ in completion() }
    }

    private func presentPublishReviewAlert(
        for review: PublishReview,
        completion: @escaping () -> Void
    ) {
        let approveAction = CPAlertAction(title: "Approve", style: .default) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.approvePublishingReview(review.id)
                await self.loadPublishing()
            }
        }
        let reviseAction = CPAlertAction(title: "Revise", style: .destructive) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.requestPublishingRevision(review.id)
                await self.loadPublishing()
            }
        }
        let cancelAction = CPAlertAction(title: "Close", style: .cancel) { _ in }
        let alert = CPAlertTemplate(
            titleVariants: [review.title],
            actions: [approveAction, reviseAction, cancelAction]
        )
        interfaceController.presentTemplate(alert, animated: true) { _, _ in completion() }
    }

    private func presentPublishChecklistAlert(completion: @escaping () -> Void) {
        guard
            let workspace = publishLaunchWorkspace,
            let nextStep = workspace.checklist.first(where: { !$0.completed }),
            !workspace.projectId.isEmpty
        else {
            completion()
            return
        }
        let completeAction = CPAlertAction(title: "Complete", style: .default) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.updatePublishingChecklistStep(
                    projectId: workspace.projectId,
                    step: nextStep.step,
                    completed: true
                )
                await self.loadPublishing()
            }
        }
        let cancelAction = CPAlertAction(title: "Close", style: .cancel) { _ in }
        let alert = CPAlertTemplate(
            titleVariants: [nextStep.label, "Mark this launch checklist step complete?"],
            actions: [completeAction, cancelAction]
        )
        interfaceController.presentTemplate(alert, animated: true) { _, _ in completion() }
    }

    private func presentOpsFocusAlert(for candidate: CarPlayOpsFocusCandidate) {
        let applyAction = CPAlertAction(title: "Set Focus", style: .default) { [weak self] _ in
            guard let self else { return }
            Task {
                let reason = "CarPlay elevated \(candidate.module) as the next live operating focus."
                _ = try? await self.client.saveCarPlayOpsFocus(
                    module: candidate.module,
                    route: candidate.route,
                    reason: reason
                )
                await self.loadOps()
            }
        }
        let cancelAction = CPAlertAction(title: "Close", style: .cancel) { _ in }
        let alert = CPAlertTemplate(
            titleVariants: [candidate.label, "Promote \(candidate.module) into shared progress focus?"],
            actions: [applyAction, cancelAction]
        )
        interfaceController.presentTemplate(alert, animated: true, completion: nil)
    }

    private func presentOpsApprovalAlert(for approval: CarPlayApprovalEntry) {
        let approveAction = CPAlertAction(title: "Approve", style: .default) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.approve(requestId: approval.requestId)
                await self.refreshAll()
            }
        }
        let cancelAction = CPAlertAction(title: "Close", style: .cancel) { _ in }
        let alert = CPAlertTemplate(
            titleVariants: [approval.title, "\(approval.agent) · \(approval.risk.capitalized) risk"],
            actions: [approveAction, cancelAction]
        )
        interfaceController.presentTemplate(alert, animated: true, completion: nil)
    }

    private func presentCarPlayAgentAlert(for agent: CarPlayAgentOpsEntry) {
        let queueAction = CPAlertAction(title: agent.queueActionLabel, style: .default) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.queueCarPlayAgentRun(agent.agentId)
                await self.loadOps()
            }
        }
        let cancelAction = CPAlertAction(title: "Close", style: .cancel) { _ in }
        let alert = CPAlertTemplate(
            titleVariants: [agent.name, agent.attentionReason.isEmpty ? agent.purpose : agent.attentionReason],
            actions: [queueAction, cancelAction]
        )
        interfaceController.presentTemplate(alert, animated: true, completion: nil)
    }

    private func presentCarPlaySupervisionAlert(for item: CarPlaySupervisionEntry) {
        let approveAction = CPAlertAction(title: item.approveLabel, style: .default) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.resolveCarPlaySupervision(
                    item.requestId,
                    action: "approve",
                    reason: "CarPlay approved \(item.title) from the supervision lane."
                )
                await self.refreshAll()
            }
        }
        let rejectAction = CPAlertAction(title: item.rejectLabel, style: .destructive) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.resolveCarPlaySupervision(
                    item.requestId,
                    action: "reject",
                    reason: "CarPlay rejected \(item.title) from the supervision lane to request a safer path."
                )
                await self.refreshAll()
            }
        }
        let cancelAction = CPAlertAction(title: "Close", style: .cancel) { _ in }
        let alert = CPAlertTemplate(
            titleVariants: [item.title, item.detail],
            actions: [approveAction, rejectAction, cancelAction]
        )
        interfaceController.presentTemplate(alert, animated: true, completion: nil)
    }

    private func presentCarPlayHuddleSummaryAlert(summary: CarPlayHuddleSummary) {
        let focusAction = CPAlertAction(title: "Set Focus", style: .default) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.saveCarPlayOpsFocus(
                    module: "Huddle",
                    route: "/huddle-center",
                    reason: "CarPlay elevated Huddle as the next live operating focus."
                )
                await self.loadOps()
            }
        }
        let partyModeAction = CPAlertAction(
            title: summary.partyModeStatus.lowercased() == "running" ? "Refresh Huddle" : "Wake Agents",
            style: .default
        ) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.startCarPlayHuddlePartyMode()
                await self.loadOps()
            }
        }
        let cancelAction = CPAlertAction(title: "Close", style: .cancel) { _ in }
        let alert = CPAlertTemplate(
            titleVariants: ["Huddle Chamber", summary.headline],
            actions: [focusAction, partyModeAction, cancelAction]
        )
        interfaceController.presentTemplate(alert, animated: true, completion: nil)
    }

    private func presentCarPlayHuddleIdeaAlert(for idea: CarPlayHuddleIdeaEntry) {
        let queueAction = CPAlertAction(title: "Queue", style: .default) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.queueCarPlayHuddleIdea(idea.id)
                await self.loadOps()
            }
        }
        let researchAction = CPAlertAction(title: "Research", style: .default) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.researchCarPlayHuddleIdeaNow(idea.id)
                await self.loadOps()
            }
        }
        let passAction = CPAlertAction(title: "Pass", style: .destructive) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.passCarPlayHuddleIdea(idea.id)
                await self.loadOps()
            }
        }
        let cancelAction = CPAlertAction(title: "Close", style: .cancel) { _ in }
        let alert = CPAlertTemplate(
            titleVariants: [idea.text, "\(idea.domain.capitalized) · \(idea.status.replacingOccurrences(of: "_", with: " ").capitalized)"],
            actions: [queueAction, researchAction, passAction, cancelAction]
        )
        interfaceController.presentTemplate(alert, animated: true, completion: nil)
    }

    private func presentCarPlayChronicleSummaryAlert(summary: CarPlayChronicleSummary) {
        let focusAction = CPAlertAction(title: "Set Focus", style: .default) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.saveCarPlayOpsFocus(
                    module: "Legacy",
                    route: "/chronicle-center",
                    reason: "CarPlay elevated Legacy as the next live operating focus."
                )
                await self.loadOps()
            }
        }
        let closeAction = CPAlertAction(title: "Close", style: .cancel) { _ in }
        let alert = CPAlertTemplate(
            titleVariants: ["Legacy Chamber", summary.headline],
            actions: [focusAction, closeAction]
        )
        interfaceController.presentTemplate(alert, animated: true, completion: nil)
    }

    private func presentCarPlayChronicleReviewAlert(for review: CarPlayChronicleReviewEntry) {
        let studyAction = CPAlertAction(title: "Study Next", style: .default) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.reviewChronicleEntry(
                    review.entryId,
                    payload: ChronicleReviewPayload(status: "study", title: review.entryTitle, entryType: review.entryType)
                )
                await self.loadOps()
            }
        }
        let familyAction = CPAlertAction(title: "Family Handoff", style: .default) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.reviewChronicleEntry(
                    review.entryId,
                    payload: ChronicleReviewPayload(status: "family", title: review.entryTitle, entryType: review.entryType)
                )
                await self.loadOps()
            }
        }
        let resolveAction = CPAlertAction(title: "Resolve", style: .destructive) { [weak self] _ in
            guard let self else { return }
            Task {
                _ = try? await self.client.reviewChronicleEntry(
                    review.entryId,
                    payload: ChronicleReviewPayload(status: "resolved", title: review.entryTitle, entryType: review.entryType)
                )
                await self.loadOps()
            }
        }
        let closeAction = CPAlertAction(title: "Close", style: .cancel) { _ in }
        let alert = CPAlertTemplate(
            titleVariants: [review.entryTitle, "\(review.reviewStatusLabel) · \(review.entryType.capitalized)"],
            actions: [studyAction, familyAction, resolveAction, closeAction]
        )
        interfaceController.presentTemplate(alert, animated: true, completion: nil)
    }
}
