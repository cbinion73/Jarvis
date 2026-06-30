import Testing
@testable import JarvisKit

struct CarPlayPresentationTests {
    @Test
    func prefersCurrentLocationLabelWhenNavigationStateUsesCurrentOrigin() {
        let overview = NavigationLocationsOverview(
            preferredLocationId: "home-base",
            savedLocations: [
                NavigationSavedLocation(
                    id: "home-base",
                    label: "Home",
                    address: "8384 Riley Rd, Alexandria, KY 41001",
                    geography: "Alexandria, KY",
                    latitude: nil,
                    longitude: nil,
                    source: "manual",
                    notes: ""
                ),
            ],
            navigationState: NavigationState(
                favoriteDestinations: [],
                recentDestinations: [],
                routeHistory: [],
                activeStopCategoryIDs: [],
                parksHistoricRadiusMiles: 25,
                selectedOriginMode: "current",
                selectedSavedLocationID: "home-base",
                lastRoute: NavigationLastRoute(origin: "Current Location", destination: "Cincinnati, OH")
            )
        )

        #expect(JarvisCarPlayPresentation.preferredOriginLabel(from: overview) == "Current Location")
    }

    @Test
    func buildsNavigationChoicesFromSavedFavoriteAndRecentDestinationsWithoutDuplicates() {
        let overview = NavigationLocationsOverview(
            preferredLocationId: "home-base",
            savedLocations: [
                NavigationSavedLocation(
                    id: "home-base",
                    label: "Home",
                    address: "8384 Riley Rd, Alexandria, KY 41001",
                    geography: "Alexandria, KY",
                    latitude: nil,
                    longitude: nil,
                    source: "manual",
                    notes: ""
                ),
                NavigationSavedLocation(
                    id: "work",
                    label: "Work",
                    address: "500 Market St, Cincinnati, OH",
                    geography: "Cincinnati, OH",
                    latitude: nil,
                    longitude: nil,
                    source: "manual",
                    notes: ""
                ),
            ],
            navigationState: NavigationState(
                favoriteDestinations: ["Work", "Grandma's House"],
                recentDestinations: ["Cincinnati, OH", "Grandma's House"],
                routeHistory: [],
                activeStopCategoryIDs: ["food", "parks"],
                parksHistoricRadiusMiles: 25,
                selectedOriginMode: "home",
                selectedSavedLocationID: "home-base",
                lastRoute: NavigationLastRoute(origin: "Home", destination: "Cincinnati, OH")
            )
        )

        let choices = JarvisCarPlayPresentation.navigationChoices(from: overview)
        let titles = choices.map { $0.title }
        let sources = choices.map { $0.source }

        #expect(choices.count == 4)
        #expect(titles == ["Home", "Work", "Grandma's House", "Cincinnati, OH"])
        #expect(sources == [.saved, .saved, .favorite, .recent])
        #expect(JarvisCarPlayPresentation.preferredOriginLabel(from: overview) == "8384 Riley Rd, Alexandria, KY 41001")
    }

    @Test
    func includesRouteHistoryChoicesWithoutDuplicatingExistingDestinations() {
        let overview = NavigationLocationsOverview(
            preferredLocationId: nil,
            savedLocations: [
                NavigationSavedLocation(
                    id: "home-base",
                    label: "Home",
                    address: "8384 Riley Rd, Alexandria, KY 41001",
                    geography: "Alexandria, KY",
                    latitude: nil,
                    longitude: nil,
                    source: "manual",
                    notes: ""
                ),
            ],
            navigationState: NavigationState(
                favoriteDestinations: ["Retirement Workshop"],
                recentDestinations: ["Cincinnati, OH"],
                routeHistory: [
                    NavigationRouteHistoryEntry(
                        routeID: "history-1",
                        origin: "Home",
                        destination: "Retirement Workshop",
                        originMode: "home",
                        savedLocationID: "home-base",
                        sourceLabel: "history",
                        savedAt: "2026-06-27T10:00:00Z",
                        lastPreviewedAt: "2026-06-27T10:05:00Z",
                        lastResumedAt: "2026-06-27T10:06:00Z",
                        previewCount: 1,
                        resumeCount: 1
                    ),
                    NavigationRouteHistoryEntry(
                        routeID: "history-2",
                        origin: "Home",
                        destination: "Louisville, KY",
                        originMode: "home",
                        savedLocationID: "home-base",
                        sourceLabel: "history",
                        savedAt: "2026-06-27T10:00:00Z",
                        lastPreviewedAt: "2026-06-27T10:05:00Z",
                        lastResumedAt: "2026-06-27T10:06:00Z",
                        previewCount: 1,
                        resumeCount: 1
                    ),
                ],
                activeStopCategoryIDs: [],
                parksHistoricRadiusMiles: 25,
                selectedOriginMode: "home",
                selectedSavedLocationID: "home-base",
                lastRoute: NavigationLastRoute(origin: "Home", destination: "Louisville, KY")
            )
        )

        let choices = JarvisCarPlayPresentation.navigationChoices(from: overview)
        let titles = choices.map(\.title)
        let sources = choices.map(\.source)

        #expect(titles == ["Home", "Retirement Workshop", "Cincinnati, OH", "Louisville, KY"])
        #expect(sources == [.saved, .favorite, .recent, .routeHistory])
    }

    @Test
    func buildsCurrentRouteHeadlineAndPublishQueueSummaries() {
        let route = NavigationRouteOverview(
            origin: NavigationPoint(label: "Home", lat: 0, lon: 0),
            destination: NavigationPoint(label: "Cincinnati, OH", lat: 1, lon: 1),
            summary: "Leave by 9:38 AM for best traffic.",
            hazardActive: true,
            route: NavigationRouteShape(
                distanceMiles: 82,
                durationMinutes: 84,
                coordinates: [],
                steps: []
            ),
            samples: []
        )
        let routeHeadline = JarvisCarPlayPresentation.currentRouteHeadline(
            state: NavigationState(
                favoriteDestinations: [],
                recentDestinations: [],
                routeHistory: [],
                activeStopCategoryIDs: [],
                parksHistoricRadiusMiles: 25,
                selectedOriginMode: "home",
                selectedSavedLocationID: "",
                lastRoute: NavigationLastRoute(origin: "Home", destination: "Cincinnati, OH")
            ),
            route: route
        )

        #expect(routeHeadline?.title == "Home -> Cincinnati, OH")
        #expect(routeHeadline?.detail.contains("82 mi") == true)
        #expect(routeHeadline?.detail.contains("Hazard active") == true)

        let publish = PublishOverview(
            projects: [],
            revenueSummary: RevenueSummary(monthlyEstimate: 0, streamCount: 0, streams: []),
            upcoming: [],
            pendingReviews: [
                PublishReview(
                    reviewId: "rev-1",
                    title: "Systems of Influence",
                    slug: "systems-of-influence",
                    stageKey: "editorial_review",
                    stageDisplay: "Editorial Review",
                    contentPreview: "Preview",
                    wordCount: 58420,
                    readySince: "2026-06-06T04:00:00Z",
                    approvalId: "approval-1"
                )
            ],
            pendingReviewsCount: 1,
            launchControl: nil,
            launchWorkspace: nil,
            actionItems: [],
            continuity: nil,
            updatedAt: ""
        )

        let queue = JarvisCarPlayPresentation.publishQueue(from: publish)
        #expect(queue.count == 1)
        #expect(queue[0].title == "Systems of Influence")
        #expect(queue[0].stageDisplay == "Editorial Review")
        #expect(queue[0].detail.contains("58420 words") == true)
    }

    @Test
    func routeDetailIncludesOnlyTheSegmentsThatActuallyExist() {
        let route = NavigationRouteOverview(
            origin: NavigationPoint(label: "Home", lat: 0, lon: 0),
            destination: NavigationPoint(label: "Scout Campout", lat: 1, lon: 1),
            summary: "",
            hazardActive: false,
            route: NavigationRouteShape(
                distanceMiles: nil,
                durationMinutes: 23,
                coordinates: [],
                steps: []
            ),
            samples: []
        )

        #expect(JarvisCarPlayPresentation.routeDetail(for: route) == "23 min")
    }
}
