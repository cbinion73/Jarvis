import CarPlay
import JarvisKit

/// Manages the full CarPlay template hierarchy for JARVIS.
///
/// Layout:
/// ```
/// CPTabBarTemplate
///   ├── Brief    — CPListTemplate   (morning intelligence)
///   ├── Needs    — CPListTemplate   (pending approvals)
///   └── Status   — CPInformationTemplate (health + mode)
/// ```
///
/// All network calls run on a background Task so the CarPlay runloop stays
/// responsive. Templates are set to loading state, then updated in-place.
@MainActor
final class JarvisCarPlayController: NSObject, @preconcurrency CPListTemplateDelegate {

    // MARK: - Properties

    private let interfaceController: CPInterfaceController
    private var refreshTimer: Timer?

    private let client = AppleAPIClient.shared

    // Root
    private var tabBar: CPTabBarTemplate?

    // Tab templates
    private let briefTemplate  = CPListTemplate(title: "JARVIS Brief",  sections: [])
    private let needsTemplate  = CPListTemplate(title: "Needs You",     sections: [])

    // Needs data — kept in sync with displayed rows
    private var pendingNeeds: [NeedsItem] = []

    // MARK: - Init

    init(interfaceController: CPInterfaceController) {
        self.interfaceController = interfaceController
        super.init()
    }

    // MARK: - Lifecycle

    func start() {
        briefTemplate.tabImage  = UIImage(systemName: "sun.horizon.fill")
        needsTemplate.tabImage  = UIImage(systemName: "exclamationmark.circle.fill")
        needsTemplate.delegate  = self

        let tab = CPTabBarTemplate(templates: [briefTemplate, needsTemplate])
        self.tabBar = tab

        interfaceController.setRootTemplate(tab, animated: false, completion: nil)

        // Load data immediately then refresh every 90 s
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

    // MARK: - Data refresh

    private func refreshAll() async {
        async let briefing = loadBriefing()
        async let needs    = loadNeeds()
        _ = await (briefing, needs)
    }

    // MARK: - Brief tab

    private func loadBriefing() async {
        do {
            let packet = try await client.fetchBriefing()
            let sections = buildBriefSections(from: packet)
            briefTemplate.updateSections(sections)
        } catch {
            briefTemplate.updateSections([
                CPListSection(items: [
                    CPListItem(text: "Couldn't load briefing", detailText: error.localizedDescription)
                ])
            ])
        }
    }

    private func buildBriefSections(from packet: BriefingPacket) -> [CPListSection] {
        var sections: [CPListSection] = []

        // Greeting
        let greetItem = CPListItem(text: packet.greeting, detailText: packet.mode.capitalized + " mode")
        greetItem.setImage(UIImage(systemName: "brain.head.profile"))
        sections.append(CPListSection(items: [greetItem], header: nil, sectionIndexTitle: nil))

        // Briefing items (top 6 for readability)
        if !packet.briefingItems.isEmpty {
            let items: [CPListItem] = packet.briefingItems.prefix(6).map { item in
                let li = CPListItem(text: item.text, detailText: item.agent)
                if item.priority == "high" {
                    li.setImage(UIImage(systemName: "exclamationmark.circle.fill")?
                        .withTintColor(.systemOrange, renderingMode: .alwaysOriginal))
                }
                return li
            }
            sections.append(CPListSection(items: items, header: "Intelligence", sectionIndexTitle: nil))
        }

        // Active agents (top 3)
        if !packet.workingItems.isEmpty {
            let items: [CPListItem] = packet.workingItems.prefix(3).map { item in
                CPListItem(text: item.agent, detailText: item.action)
            }
            sections.append(CPListSection(items: items, header: "Agents Working", sectionIndexTitle: nil))
        }

        return sections
    }

    // MARK: - Needs tab

    private func loadNeeds() async {
        do {
            let needs = try await client.fetchNeeds()

            if needs.isEmpty {
                let item = CPListItem(text: "All clear", detailText: "No approvals waiting")
                item.setImage(UIImage(systemName: "checkmark.circle.fill")?
                    .withTintColor(.systemGreen, renderingMode: .alwaysOriginal))
                needsTemplate.updateSections([CPListSection(items: [item])])
                return
            }

            // Store needs so the delegate can reference them by index
            self.pendingNeeds = needs

            let items: [CPListItem] = needs.map { need in
                let li = CPListItem(text: need.text, detailText: need.agent, image: riskImage(for: need.risk), showsDisclosureIndicator: false)
                return li
            }

            needsTemplate.updateSections([
                CPListSection(items: items, header: "\(needs.count) pending", sectionIndexTitle: nil)
            ])

        } catch {
            let item = CPListItem(text: "Couldn't load", detailText: error.localizedDescription)
            needsTemplate.updateSections([CPListSection(items: [item])])
        }
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

    // MARK: - CPListTemplateDelegate

    func listTemplate(
        _ listTemplate: CPListTemplate,
        didSelect item: CPListItem,
        completionHandler: @escaping () -> Void
    ) {
        guard listTemplate === needsTemplate else { completionHandler(); return }
        guard let idx = needsTemplate.sections.first?.items.firstIndex(where: { $0 === item }),
              idx < pendingNeeds.count else { completionHandler(); return }
        let need = pendingNeeds[idx]
        presentApproveAlert(for: need, completion: completionHandler)
    }

    // MARK: - Approve alert

    private func presentApproveAlert(
        for need: NeedsItem,
        completion: @escaping () -> Void
    ) {
        let approveAction = CPAlertAction(
            title: "Approve",
            style: .default
        ) { [weak self] _ in
            guard let self else { return }
            Task {
                try? await self.client.approve(requestId: need.id)
                await self.loadNeeds()
            }
        }

        let cancelAction = CPAlertAction(title: "Cancel", style: .cancel) { _ in }

        let alert = CPAlertTemplate(
            titleVariants: [need.text],
            actions: [approveAction, cancelAction]
        )

        interfaceController.presentTemplate(alert, animated: true) { _, _ in
            completion()
        }
    }
}
