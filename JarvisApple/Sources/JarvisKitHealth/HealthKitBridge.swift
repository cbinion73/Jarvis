import Foundation

#if canImport(HealthKit)
import HealthKit

public final class HealthKitBridge {
    public let store = HKHealthStore()

    public init() {}

    public static var isAvailable: Bool {
        HKHealthStore.isHealthDataAvailable()
    }
}
#else
public final class HealthKitBridge {
    public init() {}

    public static var isAvailable: Bool {
        false
    }
}
#endif
