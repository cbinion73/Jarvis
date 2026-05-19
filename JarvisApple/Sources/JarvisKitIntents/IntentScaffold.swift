import Foundation

#if canImport(AppIntents)
import AppIntents

@available(iOS 18.0, macOS 15.0, watchOS 11.0, tvOS 18.0, *)
public struct ShowHealthSummaryIntentScaffold: AppIntent {
    public static var title: LocalizedStringResource = "Show Health Summary"

    public init() {}

    public func perform() async throws -> some IntentResult {
        .result()
    }
}
#endif
