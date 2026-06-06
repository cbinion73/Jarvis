import Foundation

public struct CarPlayNavigationChoice: Equatable, Identifiable, Sendable {
    public enum Source: String, Equatable, Sendable {
        case saved
        case favorite
        case recent
    }

    public let id: String
    public let title: String
    public let detail: String
    public let destination: String
    public let source: Source

    public init(
        id: String,
        title: String,
        detail: String,
        destination: String,
        source: Source
    ) {
        self.id = id
        self.title = title
        self.detail = detail
        self.destination = destination
        self.source = source
    }
}

public struct CarPlayPublishQueueEntry: Equatable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let detail: String
    public let stageDisplay: String

    public init(id: String, title: String, detail: String, stageDisplay: String) {
        self.id = id
        self.title = title
        self.detail = detail
        self.stageDisplay = stageDisplay
    }
}

public enum JarvisCarPlayPresentation {
    public static func preferredOriginLabel(from overview: NavigationLocationsOverview) -> String {
        let state = overview.navigationState
        if state?.selectedOriginMode.lowercased() == "current" {
            return "Current Location"
        }
        if let preferredId = overview.preferredLocationId,
           let preferred = overview.savedLocations.first(where: { $0.id == preferredId }) {
            return preferred.address.isEmpty ? preferred.label : preferred.address
        }
        if let selectedId = state?.selectedSavedLocationID,
           let selected = overview.savedLocations.first(where: { $0.id == selectedId }) {
            return selected.address.isEmpty ? selected.label : selected.address
        }
        if let first = overview.savedLocations.first {
            return first.address.isEmpty ? first.label : first.address
        }
        return "Home"
    }

    public static func navigationChoices(
        from overview: NavigationLocationsOverview,
        limit: Int = 8
    ) -> [CarPlayNavigationChoice] {
        var seenDestinations = Set<String>()
        var seenTitles = Set<String>()
        var choices: [CarPlayNavigationChoice] = []

        func appendChoice(
            id: String,
            title: String,
            detail: String,
            destination: String,
            source: CarPlayNavigationChoice.Source
        ) {
            let trimmedDestination = destination.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmedDestination.isEmpty else { return }
            let dedupeKey = trimmedDestination.lowercased()
            let titleKey = title.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
            guard !seenDestinations.contains(dedupeKey), !seenTitles.contains(titleKey) else { return }
            seenDestinations.insert(dedupeKey)
            seenTitles.insert(titleKey)
            choices.append(
                CarPlayNavigationChoice(
                    id: id,
                    title: title,
                    detail: detail,
                    destination: trimmedDestination,
                    source: source
                )
            )
        }

        for location in overview.savedLocations {
            appendChoice(
                id: "saved:\(location.id)",
                title: location.label,
                detail: location.address.isEmpty ? location.geography : location.address,
                destination: location.address.isEmpty ? location.label : location.address,
                source: .saved
            )
        }

        for favorite in overview.navigationState?.favoriteDestinations ?? [] {
            appendChoice(
                id: "favorite:\(favorite)",
                title: favorite,
                detail: "Favorite destination",
                destination: favorite,
                source: .favorite
            )
        }

        for recent in overview.navigationState?.recentDestinations ?? [] {
            appendChoice(
                id: "recent:\(recent)",
                title: recent,
                detail: "Recent destination",
                destination: recent,
                source: .recent
            )
        }

        return Array(choices.prefix(limit))
    }

    public static func currentRouteHeadline(
        state: NavigationState?,
        route: NavigationRouteOverview?
    ) -> (title: String, detail: String)? {
        let origin = route?.origin.label ?? state?.lastRoute.origin ?? ""
        let destination = route?.destination.label ?? state?.lastRoute.destination ?? ""
        guard !origin.isEmpty, !destination.isEmpty else { return nil }

        let detailParts = [
            route?.summary,
            route.flatMap { routeDetail(for: $0) },
        ]
            .compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }

        return (
            title: "\(origin) -> \(destination)",
            detail: detailParts.joined(separator: " · ")
        )
    }

    public static func routeDetail(for route: NavigationRouteOverview) -> String {
        var details: [String] = []
        if let distance = route.route.distanceMiles {
            details.append(String(format: "%.0f mi", distance))
        }
        if let duration = route.route.durationMinutes {
            details.append("\(duration) min")
        }
        if route.hazardActive {
            details.append("Hazard active")
        }
        return details.joined(separator: " · ")
    }

    public static func publishQueue(
        from overview: PublishOverview,
        limit: Int = 6
    ) -> [CarPlayPublishQueueEntry] {
        Array(overview.pendingReviews.prefix(limit)).map { review in
            let stage = review.stageDisplay.isEmpty ? review.stageKey : review.stageDisplay
            let summaryBits = [
                stage.trimmingCharacters(in: .whitespacesAndNewlines),
                review.wordCount > 0 ? "\(review.wordCount) words" : "",
                review.readySince.isEmpty ? "" : review.readySince,
            ].filter { !$0.isEmpty }
            return CarPlayPublishQueueEntry(
                id: review.id,
                title: review.title,
                detail: summaryBits.joined(separator: " · "),
                stageDisplay: stage
            )
        }
    }
}
