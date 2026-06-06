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
    private let opsTemplate = CPListTemplate(title: "Catalyst", sections: [])

    private var pendingNeeds: [NeedsItem] = []
    private var navigationChoices: [CarPlayNavigationChoice] = []
    private var navigationOverview: NavigationLocationsOverview?
    private var currentRoute: NavigationRouteOverview?
    private var activeRouteStops: [NavigationStop] = []
    private var activeRouteTemplate: CPListTemplate?
    private var routeCurrentItemSelectable = false
    private var publishQueue: [CarPlayPublishQueueEntry] = []
    private var publishReviews: [PublishReview] = []
    private var publishLaunchWorkspace: PublishLaunchWorkspace?
    private var publishHistory: [PublishHistoryEntry] = []
    private var opsOverview: CarPlayOpsOverview?

    init(interfaceController: CPInterfaceController) {
        self.interfaceController = interfaceController
        super.init()
    }

    func start() {
        briefTemplate.tabImage = UIImage(systemName: "sun.horizon.fill")
        needsTemplate.tabImage = UIImage(systemName: "exclamationmark.circle.fill")
        routeTemplate.tabImage = UIImage(systemName: "map.fill")
        publishTemplate.tabImage = UIImage(systemName: "doc.richtext.fill")
        opsTemplate.tabImage = UIImage(systemName: "square.grid.2x2.fill")

        needsTemplate.delegate = self
        routeTemplate.delegate = self
        publishTemplate.delegate = self
        opsTemplate.delegate = self

        let tab = CPTabBarTemplate(templates: [briefTemplate, needsTemplate, routeTemplate, publishTemplate, opsTemplate])
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
        async let ops = loadOps()
        _ = await (briefing, needs, route, publish, ops)
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
                text: "Navigation Command Center",
                detailText: routeHeadline?.detail.isEmpty == false
                    ? routeHeadline?.detail
                    : "Live route timing, hazard posture, and smart stop continuity."
            )
            overviewItem.setImage(
                UIImage(systemName: "point.bottomleft.forward.to.point.topright.scurvepath")?
                    .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
            )
            let weatherItem = CPListItem(
                text: "Weather Along Route",
                detailText: currentRoute?.hazardActive == true
                    ? "Hazard active. Use voice guidance before leaving."
                    : "No major route hazard surfaced in the live preview."
            )
            weatherItem.setImage(
                UIImage(systemName: "cloud.sun.rain.fill")?
                    .withTintColor(.systemTeal, renderingMode: .alwaysOriginal)
            )
            sections.append(CPListSection(items: [overviewItem, weatherItem], header: "1. Navigation Command Center", sectionIndexTitle: nil))

            routeCurrentItemSelectable = routeHeadline != nil
            if let routeHeadline {
                let currentItem = CPListItem(text: routeHeadline.title, detailText: routeHeadline.detail)
                currentItem.setImage(
                    UIImage(systemName: "point.bottomleft.forward.to.point.topright.scurvepath")?
                        .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
                )
                let voiceItem = CPListItem(
                    text: "Voice Navigation",
                    detailText: currentRoute?.hazardActive == true
                        ? "Ask JARVIS about weather, delays, and leave-by timing."
                        : "Hands-free guidance is ready for the next route question."
                )
                voiceItem.setImage(
                    UIImage(systemName: "waveform")?
                        .withTintColor(.systemGreen, renderingMode: .alwaysOriginal)
                )
                sections.append(CPListSection(items: [currentItem, voiceItem], header: "2. Active Route & Voice Consultation", sectionIndexTitle: nil))
            }

            if navigationChoices.isEmpty {
                let item = CPListItem(text: "No destinations yet", detailText: "Save family places or recent trips from the phone app.")
                sections.append(CPListSection(items: [item], header: "3. Smart Destinations", sectionIndexTitle: nil))
            } else {
                let items = navigationChoices.map { choice in
                    let item = CPListItem(text: choice.title, detailText: choice.detail)
                    item.setImage(icon(for: choice.source))
                    return item
                }
                sections.append(CPListSection(items: items, header: "3. Smart Destinations", sectionIndexTitle: nil))
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
            sections.append(CPListSection(items: [originItem, plannerItem, orchestrationItem], header: "4. Planner & Travel Orchestration", sectionIndexTitle: nil))
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
                text: "Chronicle Chamber",
                detailText: chronicleSummary.headline
            )
            chronicleSummaryItem.setImage(
                UIImage(systemName: "book.closed.fill")?
                    .withTintColor(.systemYellow, renderingMode: .alwaysOriginal)
            )
            let chroniclePromptItem = CPListItem(
                text: chronicleSummary.latestTitle.isEmpty ? "No Chronicle thread ready" : chronicleSummary.latestTitle,
                detailText: chronicleSummary.studyTitle.isEmpty
                    ? "\(chronicleSummary.activePrayerCount) active prayer(s) · \(chronicleSummary.reviewCount) review thread(s)"
                    : "\(chronicleSummary.studyTitle) · \(chronicleSummary.reviewCount) review thread(s)"
            )
            chroniclePromptItem.setImage(
                UIImage(systemName: "text.book.closed.fill")?
                    .withTintColor(.systemOrange, renderingMode: .alwaysOriginal)
            )
            sections.append(CPListSection(items: [chronicleSummaryItem, chroniclePromptItem], header: "9. Chronicle Chamber", sectionIndexTitle: nil))

            let chronicleReviewItems: [CPListItem]
            if overview.chronicleReviews.isEmpty {
                let item = CPListItem(text: "No Chronicle review waiting", detailText: "Move a memory thread into study or family handoff from the phone.")
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
            sections.append(CPListSection(items: chronicleReviewItems, header: "10. Chronicle Reviews", sectionIndexTitle: nil))

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

        if listTemplate === activeRouteTemplate {
            Task {
                await handleRouteDetailSelection(indexPath: indexPath)
                completionHandler()
            }
            return
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
        let stopSectionIndex = template.sections.firstIndex { $0.header == "Smart Stops" }
        guard let stopSectionIndex, indexPath.section == stopSectionIndex, indexPath.item < activeRouteStops.count else {
            return
        }
        let stop = activeRouteStops[indexPath.item]
        presentStopDetail(stop)
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
        let chronicleSectionIndex = opsTemplate.sections.firstIndex { $0.header == "9. Chronicle Chamber" }
        if let chronicleSectionIndex, indexPath.section == chronicleSectionIndex {
            presentCarPlayChronicleSummaryAlert(summary: overview.chronicleSummary)
            return
        }
        let chronicleReviewSectionIndex = opsTemplate.sections.firstIndex { $0.header == "10. Chronicle Reviews" }
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
            sections.append(CPListSection(items: [summaryItem, recommendationItem], header: "1. Active Route", sectionIndexTitle: nil))

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
                sections.append(CPListSection(items: stepItems, header: "2. Voice & Maneuvers", sectionIndexTitle: nil))
            }

            if activeRouteStops.isEmpty {
                let item = CPListItem(text: "No smart stops surfaced", detailText: "Try a different destination from the phone app.")
                sections.append(CPListSection(items: [item], header: "3. Smart Stops Along Route", sectionIndexTitle: nil))
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
                sections.append(CPListSection(items: items, header: "3. Smart Stops Along Route", sectionIndexTitle: nil))
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
            sections.append(CPListSection(items: [consultationItem, intelligenceItem], header: "4. Route Intelligence & Voice", sectionIndexTitle: nil))

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
                    module: "Chronicle",
                    route: "/chronicle-center",
                    reason: "CarPlay elevated Chronicle as the next live operating focus."
                )
                await self.loadOps()
            }
        }
        let closeAction = CPAlertAction(title: "Close", style: .cancel) { _ in }
        let alert = CPAlertTemplate(
            titleVariants: ["Chronicle Chamber", summary.headline],
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
