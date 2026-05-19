import Testing
@testable import JarvisKitHealth

struct MockHealthSummaryServiceTests {
    @Test
    func returnsExpectedMockHeadline() async throws {
        let service = MockHealthSummaryService()
        let summary = await service.currentSummary()
        #expect(summary.headline == "Recovery looks low today.")
        #expect(summary.recommendations.isEmpty == false)
    }
}
