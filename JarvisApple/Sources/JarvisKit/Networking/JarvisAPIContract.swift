import Foundation

public enum JarvisEndpoint: String, CaseIterable, Sendable {
    case healthProfile = "/api/health/profile"
    case healthSync = "/api/health/sync"
    case healthSummary = "/api/health/summary"
    case healthRecommendations = "/api/health/recommendations"
    case healthEscalations = "/api/health/escalations"
    case healthClinicalResults = "/api/health/clinical-results"
    case healthClinicalResultImport = "/api/health/clinical-results/import"
}

public struct JarvisClientConfiguration: Equatable, Sendable {
    public let baseURL: URL

    public init(baseURL: URL) {
        self.baseURL = baseURL
    }
}

public struct HealthSyncRequest: Codable, Equatable, Sendable {
    public let source: String
    public let syncedAt: Date
    public let signals: [HealthSignal]
    public let clinicalResults: [ClinicalResult]
    public let deviceContext: DeviceContext

    public init(
        source: String,
        syncedAt: Date,
        signals: [HealthSignal],
        clinicalResults: [ClinicalResult],
        deviceContext: DeviceContext
    ) {
        self.source = source
        self.syncedAt = syncedAt
        self.signals = signals
        self.clinicalResults = clinicalResults
        self.deviceContext = deviceContext
    }
}

public struct DeviceContext: Codable, Equatable, Sendable {
    public let platform: String
    public let watchPaired: Bool
    public let healthkitAvailable: Bool

    public init(platform: String, watchPaired: Bool, healthkitAvailable: Bool) {
        self.platform = platform
        self.watchPaired = watchPaired
        self.healthkitAvailable = healthkitAvailable
    }
}
