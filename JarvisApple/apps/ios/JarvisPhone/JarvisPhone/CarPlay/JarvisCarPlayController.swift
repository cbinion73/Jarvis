import CarPlay
import JarvisKit

@MainActor
final class JarvisCarPlayController: NSObject, @preconcurrency CPListTemplateDelegate {

    private let interfaceController: CPInterfaceController
    private let client = AppleAPIClient.shared
    private var refreshTimer: Timer?

    private var tabBar: CPTabBarTemplate?

    private let briefTemplate = CPListTemplate(title: "JARVIS Brief", sections: [])
    private let needsTemplate = CPListTemplate(title: "Needs You", sections: [])
    private let routeTemplate = CPListTemplate(title: "Route", sections: [])
    private let publishTemplate = CPListTemplate(title: "Publish", sections: [])

    private var pendingNeeds: [NeedsItem] = []
    private var navigationChoices: [CarPlayNavigationChoice] = []
    private var navigationOverview: NavigationLocationsOverview?
    private var currentRoute: NavigationRouteOverview?
    private var activeRouteStops: [NavigationStop] = []
    private var activeRouteTemplate: CPListTemplate?
    private var routeCurrentItemSelectable = false
    private var publishQueue: [CarPlayPublishQueueEntry] = []
    private var publishReviews: [PublishReview] = []

    init(interfaceController: CPInterfaceController) {
        self.interfaceController = interfaceController
        super.init()
    }

    func start() {
        briefTemplate.tabImage = UIImage(systemName: "sun.horizon.fill")
        needsTemplate.tabImage = UIImage(systemName: "exclamationmark.circle.fill")
        routeTemplate.tabImage = UIImage(systemName: "map.fill")
        publishTemplate.tabImage = UIImage(systemName: "doc.richtext.fill")

        needsTemplate.delegate = self
        routeTemplate.delegate = self
        publishTemplate.delegate = self

        let tab = CPTabBarTemplate(templates: [briefTemplate, needsTemplate, routeTemplate, publishTemplate])
        tabBar = tab
        interfaceController.setRootTemplate(tab, animated: false, completion: nil)

        Task { await refreshAll() }
        refreshTimer = Timer.scheduledTimer(withTimeInterval: 90, repeats: true) { [weak self] _ in
            guard let self else { return }
            Task { await self.refreshAll() }
        }
    }

    func stop() {
        refreshTimer?.invalidate()
        refreshTimer = nil
    }

    private func refreshAll() async {
        async let briefing = loadBriefing()
        async let needs = loadNeeds()
        async let route = loadNavigation()
        async let publish = loadPublishing()
        _ = await (briefing, needs, route, publish)
    }

    private func loadBriefing() async {
        do {
            let packet = try await client.fetchBriefing()
            briefTemplate.updateSections(buildBriefSections(from: packet))
        } catch {
            briefTemplate.updateSections([
                CPListSection(items: [
                    CPListItem(text: "Couldn't load briefing", detailText: error.localizedDescription),
                ]),
            ])
        }
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
                text: "Route Intelligence",
                detailText: routeHeadline?.detail.isEmpty == false
                    ? routeHeadline?.detail
                    : "Live route timing, hazard posture, and smart stop continuity."
            )
            overviewItem.setImage(
                UIImage(systemName: "point.bottomleft.forward.to.point.topright.scurvepath")?
                    .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
            )
            sections.append(CPListSection(items: [overviewItem], header: "Command Center", sectionIndexTitle: nil))

            routeCurrentItemSelectable = routeHeadline != nil
            if let routeHeadline {
                let currentItem = CPListItem(text: routeHeadline.title, detailText: routeHeadline.detail)
                currentItem.setImage(
                    UIImage(systemName: "point.bottomleft.forward.to.point.topright.scurvepath")?
                        .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
                )
                sections.append(CPListSection(items: [currentItem], header: "Current Route", sectionIndexTitle: nil))
            }

            if navigationChoices.isEmpty {
                let item = CPListItem(text: "No destinations yet", detailText: "Save family places or recent trips from the phone app.")
                sections.append(CPListSection(items: [item], header: "Destinations", sectionIndexTitle: nil))
            } else {
                let items = navigationChoices.map { choice in
                    let item = CPListItem(text: choice.title, detailText: choice.detail)
                    item.setImage(icon(for: choice.source))
                    return item
                }
                sections.append(CPListSection(items: items, header: "Destinations", sectionIndexTitle: nil))
            }

            let originItem = CPListItem(
                text: "Origin",
                detailText: JarvisCarPlayPresentation.preferredOriginLabel(from: overview)
            )
            sections.append(CPListSection(items: [originItem], header: "Planner", sectionIndexTitle: nil))
            routeTemplate.updateSections(sections)
        } catch {
            let item = CPListItem(text: "Couldn't load route planner", detailText: error.localizedDescription)
            routeTemplate.updateSections([CPListSection(items: [item])])
        }
    }

    private func loadPublishing() async {
        do {
            let overview = try await client.fetchPublishing()
            publishReviews = overview.pendingReviews
            publishQueue = JarvisCarPlayPresentation.publishQueue(from: overview)

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

            publishTemplate.updateSections(sections)
        } catch {
            let item = CPListItem(text: "Couldn't load publish queue", detailText: error.localizedDescription)
            publishTemplate.updateSections([CPListSection(items: [item])])
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

        if listTemplate === activeRouteTemplate {
            Task {
                await handleRouteDetailSelection(indexPath: indexPath)
                completionHandler()
            }
            return
        }

        if listTemplate === publishTemplate {
            let queueSectionIndex = publishTemplate.sections.firstIndex { $0.header == "Review Queue" } ?? 0
            guard indexPath.section == queueSectionIndex, indexPath.item < publishReviews.count else {
                completionHandler()
                return
            }
            presentPublishReviewAlert(for: publishReviews[indexPath.item], completion: completionHandler)
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
        let hasCurrentRouteSection = routeCurrentItemSelectable ? 1 : 0
        if routeCurrentItemSelectable, indexPath.section == 0, let route = currentRoute {
            let origin = route.origin.label
            let destination = route.destination.label
            await presentRouteExperience(origin: origin, destination: destination, persistSelection: false)
            return
        }

        let destinationSectionIndex = hasCurrentRouteSection
        guard indexPath.section == destinationSectionIndex, indexPath.item < navigationChoices.count else {
            return
        }

        let choice = navigationChoices[indexPath.item]
        guard let overview = navigationOverview else { return }
        let origin = JarvisCarPlayPresentation.preferredOriginLabel(from: overview)

        do {
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
        } catch {
            // Continue into route presentation even if persistence fails.
        }

        await presentRouteExperience(origin: origin, destination: choice.destination, persistSelection: true)
    }

    private func handleRouteDetailSelection(indexPath: (section: Int, item: Int)) async {
        guard let template = activeRouteTemplate else { return }
        let stopSectionIndex = template.sections.firstIndex { $0.header == "Smart Stops" }
        guard let stopSectionIndex, indexPath.section == stopSectionIndex, indexPath.item < activeRouteStops.count else {
            return
        }
        let stop = activeRouteStops[indexPath.item]
        presentStopDetail(stop)
    }

    private func mergeRecentDestinations(_ destination: String, into existing: [String]) -> [String] {
        let normalized = destination.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalized.isEmpty else { return existing }
        let filtered = existing.filter { $0.caseInsensitiveCompare(normalized) != .orderedSame }
        return Array(([normalized] + filtered).prefix(8))
    }

    private func presentRouteExperience(origin: String, destination: String, persistSelection: Bool) async {
        do {
            let route = try await client.fetchNavigationRoute(origin: origin, destination: destination)
            let stops = try await client.fetchNavigationStops(origin: origin, destination: destination)
            currentRoute = route
            activeRouteStops = Array(stops.sections.flatMap(\.items).prefix(6))

            var sections: [CPListSection] = []
            let summaryItem = CPListItem(
                text: "\(route.origin.label) -> \(route.destination.label)",
                detailText: [route.summary, JarvisCarPlayPresentation.routeDetail(for: route)]
                    .filter { !$0.isEmpty }
                    .joined(separator: " · ")
            )
            summaryItem.setImage(
                UIImage(systemName: persistSelection ? "location.fill" : "location.circle.fill")?
                    .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
            )
            sections.append(CPListSection(items: [summaryItem], header: "Route Summary", sectionIndexTitle: nil))

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
                sections.append(CPListSection(items: stepItems, header: "Next Steps", sectionIndexTitle: nil))
            }

            if activeRouteStops.isEmpty {
                let item = CPListItem(text: "No smart stops surfaced", detailText: "Try a different destination from the phone app.")
                sections.append(CPListSection(items: [item], header: "Smart Stops", sectionIndexTitle: nil))
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
                sections.append(CPListSection(items: items, header: "Smart Stops", sectionIndexTitle: nil))
            }

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
                try? await self.client.approve(requestId: need.id)
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
                try? await self.client.approvePublishingReview(review.id)
                await self.loadPublishing()
            }
        }
        let reviseAction = CPAlertAction(title: "Revise", style: .destructive) { [weak self] _ in
            guard let self else { return }
            Task {
                try? await self.client.requestPublishingRevision(review.id)
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
}
