import Foundation

public struct HealthPermissionPlan: Equatable, Sendable {
    public let readCategories: [String]
    public let writeCategories: [String]

    public init(
        readCategories: [String] = [
            "sleep",
            "workouts",
            "steps",
            "active_energy",
            "resting_heart_rate",
            "heart_rate_variability",
            "weight",
            "blood_pressure",
            "blood_glucose",
            "clinical_records",
        ],
        writeCategories: [String] = []
    ) {
        self.readCategories = readCategories
        self.writeCategories = writeCategories
    }
}
